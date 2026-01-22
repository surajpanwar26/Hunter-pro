'''
Author:     Suraj
LinkedIn:   https://www.linkedin.com/in/saivigneshgolla/

Copyright (C) 2024 Suraj

License:    GNU Affero General Public License
            https://www.gnu.org/licenses/agpl-3.0.en.html
            
GitHub:     https://github.com/GodsScion/Auto_job_applier_linkedIn

version:    24.12.29.12.30
''' 


from config.secrets import *
from config.settings import showAiErrorAlerts
from config.questions import *

from modules.helpers import print_lg, critical_error_log, convert_to_json
from modules.ai.prompts import *
from modules.ai.prompt_safety import sanitize_prompt_input, wrap_delimited
import json

from tkinter import messagebox
from openai import OpenAI
from openai.types.model import Model
from openai.types.chat import ChatCompletion, ChatCompletionChunk
from typing import Literal


apiCheckInstructions = """

1. Make sure your AI API connection details like url, key, model names, etc are correct.
2. If you're using an local LLM, please check if the server is running.
3. Check if appropriate LLM and Embedding models are loaded and running.

Open `secret.py` in `/config` folder to configure your AI API connections.

ERROR:
"""

# Function to show an AI error alert
def ai_error_alert(message: str, stackTrace: Exception, title: str = "AI Connection Error") -> None:
    """
    Function to show an AI error alert and log it.
    """
    global showAiErrorAlerts
    if showAiErrorAlerts:
        result = messagebox.askquestion(title, f"{message}\n{str(stackTrace)}\n\nPause AI error alerts?", icon='error')
        if result == 'yes':
            showAiErrorAlerts = False
    critical_error_log(message, stackTrace)


# Function to check if an error occurred
def ai_check_error(response: ChatCompletion | ChatCompletionChunk) -> None:
    """
    Function to check if an error occurred.
    * Takes in `response` of type `ChatCompletion` or `ChatCompletionChunk`
    * Raises a `ValueError` if an error is found
    """
    if response.model_extra and response.model_extra.get("error"):
        raise ValueError(
            f'Error occurred with API: "{response.model_extra.get("error")}"'
        )


# Function to create an OpenAI client
def ai_create_openai_client() -> OpenAI:
    """
    Function to create an OpenAI client.
    * Takes no arguments
    * Returns an `OpenAI` object
    """
    try:
        print_lg("Creating OpenAI client...")
        if not use_AI:
            raise ValueError("AI is not enabled! Please enable it by setting `use_AI = True` in `secrets.py` in `config` folder.")
        
        client = OpenAI(base_url=llm_api_url, api_key=llm_api_key)

        models = ai_get_models_list(client)
        if "error" in models:
            raise ValueError(str(models[1]))
        if len(models) == 0:
            raise ValueError("No models are available!")
        # Convert models to list of IDs, handling both Model objects and strings
        model_ids = []
        for model in models:
            if isinstance(model, str):
                model_ids.append(model)
            elif hasattr(model, 'id'):
                model_ids.append(model.id)
        if llm_model not in model_ids:
            raise ValueError(f"Model `{llm_model}` is not found!")
        
        print_lg("---- SUCCESSFULLY CREATED OPENAI CLIENT! ----")
        print_lg(f"Using API URL: {llm_api_url}")
        print_lg(f"Using Model: {llm_model}")
        print_lg("Check './config/secrets.py' for more details.\n")
        print_lg("---------------------------------------------")

        return client
    except Exception as e:
        ai_error_alert(f"Error occurred while creating OpenAI client. {apiCheckInstructions}", e)
        return None  # type: ignore


# Function to close an OpenAI client
def ai_close_openai_client(client: OpenAI) -> None:
    """
    Function to close an OpenAI client.
    * Takes in `client` of type `OpenAI`
    * Returns no value
    """
    try:
        if client:
            print_lg("Closing OpenAI client...")
            client.close()
    except Exception as e:
        ai_error_alert("Error occurred while closing OpenAI client.", e)



# Function to get list of models available in OpenAI API
def ai_get_models_list(client: OpenAI) -> list[Model] | list[str]:
    """
    Function to get list of models available in OpenAI API.
    * Takes in `client` of type `OpenAI`
    * Returns a `list` object
    """
    try:
        print_lg("Getting AI models list...")
        if not client: raise ValueError("Client is not available!")
        models = client.models.list()
        # ai_check_error only works with ChatCompletion, not with model list
        print_lg("Available models:")
        print_lg(str(models.data), pretty=False)
        return models.data
    except Exception as e:
        critical_error_log("Error occurred while getting models list!", e)
        return ["error", str(e)]

def model_supports_temperature(model_name: str) -> bool:
    """
    Checks if the specified model supports the temperature parameter.
    
    Args:
        model_name (str): The name of the AI model.
    
    Returns:
        bool: True if the model supports temperature adjustments, otherwise False.
    """
    return model_name in ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo", "gpt-4o", "gpt-4o-mini"]

# Function to get chat completion from OpenAI API
def ai_completion(client: OpenAI, messages: list[dict], response_format: dict | None = None, temperature: float = 0, stream: bool = stream_output) -> dict | str:
    """
    Function that completes a chat and prints and formats the results of the OpenAI API calls.
    * Takes in `client` of type `OpenAI`
    * Takes in `messages` of type `list[dict]`. Example: `[{"role": "user", "content": "Hello"}]`
    * Takes in `response_format` of type `dict` for JSON representation, default is `None`
    * Takes in `temperature` of type `float` for temperature, default is `0`
    * Takes in `stream` of type `bool` to indicate if it's a streaming call or not
    * Returns a `dict` object representing JSON response, will try to convert to JSON if `response_format` is given
    """
    if not client: raise ValueError("Client is not available!")

    params = {"model": llm_model, "messages": messages, "stream": stream}

    if model_supports_temperature(llm_model):
        params["temperature"] = temperature
    if response_format and llm_spec in ["openai", "openai-like"]:
        params["response_format"] = response_format

    completion = client.chat.completions.create(**params)

    result = ""
    
    # Log response
    if stream:
        print_lg("--STREAMING STARTED")
        for chunk in completion:
            ai_check_error(chunk)
            chunkMessage = chunk.choices[0].delta.content
            if chunkMessage != None:
                result += chunkMessage
            print_lg(chunkMessage, end="", flush=True)
        print_lg("\n--STREAMING COMPLETE")
    else:
        ai_check_error(completion)
        result = completion.choices[0].message.content
    
    if response_format:
        result = convert_to_json(result)
    
    print_lg("\nAI Answer to Question:\n")
    print_lg(result, pretty=bool(response_format))
    return result


def ai_extract_skills(client: OpenAI, job_description: str, stream: bool = stream_output) -> dict | str:
    """
    Function to extract skills from job description using OpenAI API.
    * Takes in `client` of type `OpenAI`
    * Takes in `job_description` of type `str`
    * Takes in `stream` of type `bool` to indicate if it's a streaming call
    * Returns a `dict` object representing JSON response
    """
    print_lg("-- EXTRACTING SKILLS FROM JOB DESCRIPTION")
    try:
        import time
        from modules.dashboard import metrics as _m
        safe_jd = sanitize_prompt_input(job_description, max_len=8000)
        prompt = extract_skills_prompt.format(wrap_delimited("job_description", safe_jd))

        messages = [{"role": "user", "content": prompt}]
        start = time.perf_counter()
        result = ai_completion(client, messages, response_format=extract_skills_response_format, stream=stream)
        duration = time.perf_counter() - start
        try:
            _m.append_sample('jd_analysis', duration)
            _m.set_metric('jd_last', duration)
            _m.inc('jobs_processed')
        except Exception:
            pass
        return result
    except Exception as e:
        ai_error_alert(f"Error occurred while extracting skills from job description. {apiCheckInstructions}", e)
        return {}  # type: ignore


##> ------ Dheeraj Deshwal : dheeraj9811 Email:dheeraj20194@iiitd.ac.in/dheerajdeshwal9811@gmail.com - Feature ------
def ai_answer_question(
    client: OpenAI, 
    question: str, options: list[str] | None = None, question_type: Literal['text', 'textarea', 'single_select', 'multiple_select'] = 'text', 
    job_description: str | None = None, about_company: str | None = None, user_information_all: str | None = None,
    stream: bool = stream_output
) -> dict | str:
    # Instrument question answering duration into metrics
    import time
    from modules.dashboard import metrics as _m
    _m.inc('questions_answered_total')
    start_time = time.perf_counter()
    """
    Function to generate AI-based answers for questions in a form.
    
    Parameters:
    - `client`: OpenAI client instance.
    - `question`: The question being answered.
    - `options`: List of options (for `single_select` or `multiple_select` questions).
    - `question_type`: Type of question (text, textarea, single_select, multiple_select) It is restricted to one of four possible values.
    - `job_description`: Optional job description for context.
    - `about_company`: Optional company details for context.
    - `user_information_all`: information about you, AI cna use to answer question eg: Resume-like user information.
    - `stream`: Whether to use streaming AI completion.
    
    Returns:
    - `str`: The AI-generated answer.
    """

    print_lg("-- ANSWERING QUESTION using AI")
    try:
        safe_user_info = sanitize_prompt_input(user_information_all or "N/A", max_len=6000)
        safe_question = sanitize_prompt_input(question, max_len=1000)
        prompt = ai_answer_prompt.format(
            wrap_delimited("user_information", safe_user_info),
            wrap_delimited("question", safe_question),
        )
         # Append optional details if provided
        if job_description and job_description != "Unknown":
            prompt += f"\nJob Description:\n{wrap_delimited('job_description', sanitize_prompt_input(job_description, max_len=8000))}"
        if about_company and about_company != "Unknown":
            prompt += f"\nAbout the Company:\n{wrap_delimited('about_company', sanitize_prompt_input(about_company, max_len=2000))}"

        messages = [{"role": "user", "content": prompt}]
        print_lg("Prompt we are passing to AI: ", prompt)
        response =  ai_completion(client, messages, stream=stream)
        duration = time.perf_counter() - start_time
        try:
            _m.append_sample('question_answer_time', duration)
            _m.set_metric('question_last', duration)
        except Exception:
            pass
        # print_lg("Response from AI: ", response)
        return response
    except Exception as e:
        ai_error_alert(f"Error occurred while answering question. {apiCheckInstructions}", e)
        return {}  # type: ignore
##<


def ai_gen_experience(
    client: OpenAI,
    job_description: str, about_company: str,
    required_skills: dict, user_experience: dict,
    stream: bool = stream_output
) -> dict | str:
    """
    Function to generate experience description based on job requirements.
    * Takes in `client` of type `OpenAI`
    * Takes in job and user details
    * Returns a `dict` object with generated experience
    """
    print_lg("-- GENERATING EXPERIENCE DESCRIPTION")
    try:
        safe_jd = sanitize_prompt_input(job_description, max_len=8000)
        safe_skills = sanitize_prompt_input(json.dumps(required_skills, ensure_ascii=False), max_len=3000)
        safe_exp = sanitize_prompt_input(json.dumps(user_experience, ensure_ascii=False), max_len=4000)
        safe_company = sanitize_prompt_input(about_company, max_len=2000)
        prompt = (
            "Based on the following job description and required skills, generate a professional experience description that highlights relevant experience:\n\n"
            f"Job Description: {wrap_delimited('job_description', safe_jd)}\n\n"
            f"Required Skills: {wrap_delimited('required_skills', safe_skills)}\n\n"
            f"User Experience: {wrap_delimited('user_experience', safe_exp)}\n\n"
            f"About Company: {wrap_delimited('about_company', safe_company)}\n\n"
            "Generate a concise, professional experience description that would be suitable for a resume or application."
        )

        messages = [{"role": "user", "content": prompt}]
        result = ai_completion(client, messages, stream=stream)
        return {"experience_description": result}
    except Exception as e:
        ai_error_alert(f"Error occurred while generating experience description. {apiCheckInstructions}", e)
        return {}  # type: ignore



def ai_generate_resume(
    client: OpenAI, 
    job_description: str, about_company: str, required_skills: dict,
    stream: bool = stream_output
) -> dict:
    '''
    Function to generate resume. Takes in user experience and template info from config.
    '''
    try:
        safe_jd = sanitize_prompt_input(job_description, max_len=8000)
        safe_company = sanitize_prompt_input(about_company, max_len=2000)
        safe_skills = sanitize_prompt_input(json.dumps(required_skills, ensure_ascii=False), max_len=3000)
        prompt = (
            "Generate a tailored resume in JSON with fields 'summary', 'skills', 'experience'. "
            "Keep it concise and aligned to the job description.\n\n"
            f"Job Description: {wrap_delimited('job_description', safe_jd)}\n\n"
            f"Required Skills: {wrap_delimited('required_skills', safe_skills)}\n\n"
            f"About Company: {wrap_delimited('about_company', safe_company)}\n"
        )
        messages = [{"role": "user", "content": prompt}]
        result = ai_completion(client, messages, response_format={"type": "json_object"}, stream=stream)
        return result if isinstance(result, dict) else {"resume": str(result)}
    except Exception as e:
        ai_error_alert(f"Error occurred while generating resume. {apiCheckInstructions}", e)
        return {}  # type: ignore



def ai_generate_coverletter(
    client: OpenAI, 
    job_description: str, about_company: str, required_skills: dict,
    stream: bool = stream_output
) -> dict:
    '''
    Function to generate resume. Takes in user experience and template info from config.
    '''
    try:
        safe_jd = sanitize_prompt_input(job_description, max_len=8000)
        safe_company = sanitize_prompt_input(about_company, max_len=2000)
        safe_skills = sanitize_prompt_input(json.dumps(required_skills, ensure_ascii=False), max_len=3000)
        prompt = (
            "Generate a concise cover letter in JSON with fields 'subject' and 'body'.\n\n"
            f"Job Description: {wrap_delimited('job_description', safe_jd)}\n\n"
            f"Required Skills: {wrap_delimited('required_skills', safe_skills)}\n\n"
            f"About Company: {wrap_delimited('about_company', safe_company)}\n"
        )
        messages = [{"role": "user", "content": prompt}]
        result = ai_completion(client, messages, response_format={"type": "json_object"}, stream=stream)
        return result if isinstance(result, dict) else {"cover_letter": str(result)}
    except Exception as e:
        ai_error_alert(f"Error occurred while generating cover letter. {apiCheckInstructions}", e)
        return {}  # type: ignore



##< Evaluation Agents
def ai_evaluate_resume(
    client: OpenAI,
    job_description: str, about_company: str, required_skills: dict,
    resume: str,
    stream: bool = stream_output
) -> dict | str:
    """
    Function to evaluate resume against job requirements.
    """
    print_lg("-- EVALUATING RESUME")
    try:
        safe_jd = sanitize_prompt_input(job_description, max_len=8000)
        safe_skills = sanitize_prompt_input(json.dumps(required_skills, ensure_ascii=False), max_len=3000)
        safe_company = sanitize_prompt_input(about_company, max_len=2000)
        safe_resume = sanitize_prompt_input(resume, max_len=8000)
        prompt = (
            "Evaluate the following resume against the job description and provide a score out of 100 and feedback:\n\n"
            f"Job Description: {wrap_delimited('job_description', safe_jd)}\n\n"
            f"Required Skills: {wrap_delimited('required_skills', safe_skills)}\n\n"
            f"About Company: {wrap_delimited('about_company', safe_company)}\n\n"
            f"Resume: {wrap_delimited('resume', safe_resume)}\n\n"
            "Provide a JSON response with 'score' and 'feedback' fields."
        )

        messages = [{"role": "user", "content": prompt}]
        result = ai_completion(client, messages, response_format={"type": "json_object"}, stream=stream)
        return result
    except Exception as e:
        ai_error_alert(f"Error occurred while evaluating resume. {apiCheckInstructions}", e)
        return {}  # type: ignore



def ai_check_job_relevance(
    client: OpenAI,
    job_description: str, about_company: str,
    stream: bool = stream_output
) -> dict:
    """
    Function to check job relevance based on description and company info.
    """
    print_lg("-- CHECKING JOB RELEVANCE")
    try:
        safe_jd = sanitize_prompt_input(job_description, max_len=8000)
        safe_company = sanitize_prompt_input(about_company, max_len=2000)
        prompt = (
            "Analyze the following job and determine its relevance for a software developer role:\n\n"
            f"Job Description: {wrap_delimited('job_description', safe_jd)}\n\n"
            f"About Company: {wrap_delimited('about_company', safe_company)}\n\n"
            "Provide a JSON response with 'relevance_score' (0-100) and 'reasoning'."
        )

        messages = [{"role": "user", "content": prompt}]
        result = ai_completion(client, messages, response_format={"type": "json_object"}, stream=stream)
        if isinstance(result, dict):
            return result
        return {}  # type: ignore
    except Exception as e:
        ai_error_alert(f"Error occurred while checking job relevance. {apiCheckInstructions}", e)
        return {}  # type: ignore
#>