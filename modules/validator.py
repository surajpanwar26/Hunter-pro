'''
Author:     Suraj Panwar
LinkedIn:   https://www.linkedin.com/in/surajpanwar26/

Copyright (C) 2024 Suraj Panwar

License:    GNU Affero General Public License
            https://www.gnu.org/licenses/agpl-3.0.en.html
            
GitHub:     https://github.com/GodsScion/Auto_job_applier_linkedIn

version:    24.12.29.12.30
'''




# from config.XdepricatedX import *

__validation_file_path = ""

def check_int(var: int, var_name: str, min_value: int=0) -> bool | TypeError | ValueError:
    if not isinstance(var, int): raise TypeError(f'The variable "{var_name}" in "{__validation_file_path}" must be an Integer!\nReceived "{var}" of type "{type(var)}" instead!\n\nSolution:\nPlease open "{__validation_file_path}" and update "{var_name}" to be an Integer.\nExample: `{var_name} = 10`\n\nNOTE: Do NOT surround Integer values in quotes ("10")X !\n\n')
    if var < min_value: raise ValueError(f'The variable "{var_name}" in "{__validation_file_path}" expects an Integer greater than or equal to `{min_value}`! Received `{var}` instead!\n\nSolution:\nPlease open "{__validation_file_path}" and update "{var_name}" accordingly.')
    return True

def check_boolean(var: bool, var_name: str) -> bool | ValueError:
    if var == True or var == False: return True
    raise ValueError(f'The variable "{var_name}" in "{__validation_file_path}" expects a Boolean input `True` or `False`, not "{var}" of type "{type(var)}" instead!\n\nSolution:\nPlease open "{__validation_file_path}" and update "{var_name}" to either `True` or `False` (case-sensitive, T and F must be CAPITAL/uppercase).\nExample: `{var_name} = True`\n\nNOTE: Do NOT surround Boolean values in quotes ("True")X !\n\n')

def check_string(var: str, var_name: str, options: list=[], min_length: int=0) -> bool | TypeError | ValueError:
    if not isinstance(var, str): raise TypeError(f'Invalid input for {var_name}. Expecting a String!')
    if min_length > 0 and len(var) < min_length: raise ValueError(f'Invalid input for {var_name}. Expecting a String of length at least {min_length}!')
    if len(options) > 0 and var not in options: raise ValueError(f'Invalid input for {var_name}. Expecting a value from {options}, not {var}!')
    return True

def check_list(var: list, var_name: str, options: list=[], min_length: int=0) -> bool | TypeError | ValueError:
    if not isinstance(var, list): 
        raise TypeError(f'Invalid input for {var_name}. Expecting a List!')
    if len(var) < min_length: raise ValueError(f'Invalid input for {var_name}. Expecting a List of length at least {min_length}!')
    for element in var:
        if not isinstance(element, str): raise TypeError(f'Invalid input for {var_name}. All elements in the list must be strings!')
        if len(options) > 0 and element not in options: raise ValueError(f'Invalid input for {var_name}. Expecting all elements to be values from {options}. This "{element}" is NOT in options!')
    return True



from config.personals import *
def validate_personals() -> None | ValueError | TypeError:
    '''
    Validates all variables in the `/config/personals.py` file.
    '''
    global __validation_file_path
    __validation_file_path = "config/personals.py"

    check_string(first_name, "first_name", min_length=1)
    check_string(middle_name, "middle_name")
    check_string(last_name, "last_name", min_length=1)

    check_string(phone_number, "phone_number", min_length=10)

    check_string(current_city, "current_city")
    
    check_string(street, "street")
    check_string(state, "state")
    check_string(zipcode, "zipcode")
    check_string(country, "country")
    
    check_string(ethnicity, "ethnicity", ["Decline", "Hispanic/Latino", "American Indian or Alaska Native", "Asian", "Black or African American", "Native Hawaiian or Other Pacific Islander", "White", "Other"],  min_length=0)
    check_string(gender, "gender", ["Male", "Female", "Other", "Decline", ""])
    check_string(disability_status, "disability_status", ["Yes", "No", "Decline"])
    check_string(veteran_status, "veteran_status", ["Yes", "No", "Decline"])



from config.questions import *
def validate_questions() -> None | ValueError | TypeError:
    '''
    Validates all variables in the `/config/questions.py` file.
    '''
    global __validation_file_path
    __validation_file_path = "config/questions.py"

    check_string(default_resume_path, "default_resume_path")
    check_string(years_of_experience, "years_of_experience")
    check_string(require_visa, "require_visa", ["Yes", "No"])
    check_string(website, "website")
    check_string(linkedIn, "linkedIn")
    check_int(desired_salary, "desired_salary")
    check_string(us_citizenship, "us_citizenship", ["U.S. Citizen/Permanent Resident", "Non-citizen allowed to work for any employer", "Non-citizen allowed to work for current employer", "Non-citizen seeking work authorization", "Canadian Citizen/Permanent Resident", "Other"])
    check_string(linkedin_headline, "linkedin_headline")
    check_int(notice_period, "notice_period")
    check_int(current_ctc, "current_ctc")
    check_string(linkedin_summary, "linkedin_summary")
    check_string(cover_letter, "cover_letter")
    check_string(recent_employer, "recent_employer")
    check_string(confidence_level, "confidence_level")

    check_boolean(pause_before_submit, "pause_before_submit")
    check_boolean(pause_at_failed_question, "pause_at_failed_question")
    check_boolean(overwrite_previous_answers, "overwrite_previous_answers")


from config.search import *
def validate_search() -> None | ValueError | TypeError:
    '''
    Validates all variables in the `/config/search.py` file.
    '''
    global __validation_file_path
    __validation_file_path = "config/search.py"

    check_list(search_terms, "search_terms", min_length=1)
    check_string(search_location, "search_location")
    check_int(switch_number, "switch_number", 1)
    check_boolean(randomize_search_order, "randomize_search_order")

    check_string(sort_by, "sort_by", ["", "Most recent", "Most relevant"])
    check_string(date_posted, "date_posted", ["", "Any time", "Past month", "Past week", "Past 24 hours"])
    check_string(salary, "salary")

    check_boolean(easy_apply_only, "easy_apply_only")

    check_list(experience_level, "experience_level", ["Internship", "Entry level", "Associate", "Mid-Senior level", "Director", "Executive"])
    check_list(job_type, "job_type", ["Full-time", "Part-time", "Contract", "Temporary", "Volunteer", "Internship", "Other"])
    check_list(on_site, "on_site", ["On-site", "Remote", "Hybrid"])

    check_list(companies, "companies")
    check_list(location, "location")
    check_list(industry, "industry")
    check_list(job_function, "job_function")
    check_list(job_titles, "job_titles")
    check_list(benefits, "benefits")
    check_list(commitments, "commitments")

    check_boolean(under_10_applicants, "under_10_applicants")
    check_boolean(in_your_network, "in_your_network")
    check_boolean(fair_chance_employer, "fair_chance_employer")

    check_boolean(pause_after_filters, "pause_after_filters")

    check_list(about_company_bad_words, "about_company_bad_words")
    check_list(about_company_good_words, "about_company_good_words")
    check_list(bad_words, "bad_words")
    check_boolean(security_clearance, "security_clearance")
    check_boolean(did_masters, "did_masters")
    check_int(current_experience, "current_experience", -1)




from config.secrets import *
def validate_secrets() -> None | ValueError | TypeError:
    '''
    Validates all variables in the `/config/secrets.py` file.
    '''
    global __validation_file_path
    __validation_file_path = "config/secrets.py"

    check_string(username, "username", min_length=5)
    check_string(password, "password", min_length=5)

    check_boolean(use_AI, "use_AI")
    check_string(llm_api_url, "llm_api_url", min_length=5)
    check_string(llm_api_key, "llm_api_key")
    # check_string(llm_embedding_model, "llm_embedding_model")
    check_boolean(stream_output, "stream_output")
    
    ##> ------ Yang Li : MARKYangL - Feature ------
    # Validate AI provider configuration
    check_string(ai_provider, "ai_provider", ["openai", "deepseek", "gemini", "ollama"])

    ##> ------ Tim L : tulxoro - Refactor ------
    if ai_provider == "deepseek":
        check_string(llm_model, "deepseek_model", ["deepseek-chat", "deepseek-reasoner"])
    elif ai_provider == "ollama":
        check_string(ollama_model, "ollama_model")
    elif ai_provider == "gemini":
        check_string(gemini_api_key, "gemini_api_key")
    else:
        check_string(llm_model, "llm_model")
    ##<

    ##<



from config.settings import *
def validate_settings() -> None | ValueError | TypeError:
    '''
    Validates all variables in the `/config/settings.py` file.
    '''
    global __validation_file_path
    __validation_file_path = "config/settings.py"

    check_boolean(close_tabs, "close_tabs")
    check_boolean(follow_companies, "follow_companies")
    # check_boolean(connect_hr, "connect_hr")
    # check_string(connect_request_message, "connect_request_message", min_length=10)

    check_boolean(run_non_stop, "run_non_stop")
    check_boolean(alternate_sortby, "alternate_sortby")
    check_boolean(cycle_date_posted, "cycle_date_posted")
    check_boolean(stop_date_cycle_at_24hr, "stop_date_cycle_at_24hr")
    
    # check_string(generated_resume_path, "generated_resume_path", min_length=1)

    check_string(file_name, "file_name", min_length=1)
    check_string(failed_file_name, "failed_file_name", min_length=1)
    check_string(logs_folder_path, "logs_folder_path", min_length=1)

    check_int(click_gap, "click_gap", 0)

    check_boolean(run_in_background, "run_in_background")
    check_boolean(disable_extensions, "disable_extensions")
    check_boolean(safe_mode, "safe_mode")
    check_boolean(smooth_scroll, "smooth_scroll")
    check_boolean(keep_screen_awake, "keep_screen_awake")
    check_boolean(stealth_mode, "stealth_mode")




def validate_config() -> bool | ValueError | TypeError:
    '''
    Runs all validation functions to validate all variables in the config files.
    Returns True if all validations pass, raises exception with details on failure.
    '''
    errors = []
    
    try:
        validate_personals()
    except (ValueError, TypeError) as e:
        errors.append(f"personals.py: {e}")
    
    try:
        validate_questions()
    except (ValueError, TypeError) as e:
        errors.append(f"questions.py: {e}")
    
    try:
        validate_search()
    except (ValueError, TypeError) as e:
        errors.append(f"search.py: {e}")
    
    try:
        validate_secrets()
    except (ValueError, TypeError) as e:
        errors.append(f"secrets.py: {e}")
    
    try:
        validate_settings()
    except (ValueError, TypeError) as e:
        errors.append(f"settings.py: {e}")
    
    if errors:
        error_message = "Configuration validation failed:\n" + "\n".join(errors)
        raise ValueError(error_message)

    # validate_String(chatGPT_username, "chatGPT_username")
    # validate_String(chatGPT_password, "chatGPT_password")
    # validate_String(chatGPT_resume_chat_title, "chatGPT_resume_chat_title")
    return True


def check_file_exists(path: str, var_name: str) -> bool:
    '''
    Validates that a file exists at the given path.
    Returns True if exists, raises ValueError if not.
    '''
    import os
    if not os.path.exists(path):
        raise ValueError(f'The file specified in "{var_name}" does not exist: "{path}"')
    return True


def check_directory_writable(path: str, var_name: str) -> bool:
    '''
    Validates that a directory exists and is writable.
    Returns True if writable, raises ValueError if not.
    '''
    import os
    
    # Get directory from path (in case it's a file path)
    dir_path = os.path.dirname(path) if os.path.basename(path) else path
    
    if not dir_path:
        dir_path = '.'
    
    if not os.path.exists(dir_path):
        try:
            os.makedirs(dir_path, exist_ok=True)
        except (PermissionError, OSError) as e:
            raise ValueError(f'Cannot create directory for "{var_name}": {e}')
    
    if not os.access(dir_path, os.W_OK):
        raise ValueError(f'Directory is not writable for "{var_name}": "{dir_path}"')
    
    return True


def validate_environment() -> dict:
    '''
    Validates the runtime environment and returns a status dictionary.
    '''
    import sys
    import os
    
    status = {
        "python_version": sys.version,
        "platform": sys.platform,
        "working_directory": os.getcwd(),
        "checks": {}
    }
    
    # Check Python version
    if sys.version_info < (3, 9):
        status["checks"]["python_version"] = "Warning: Python 3.9+ recommended"
    else:
        status["checks"]["python_version"] = "OK"
    
    # Check for required modules
    required_modules = ["selenium", "pyautogui", "flask"]
    for module in required_modules:
        try:
            __import__(module)
            status["checks"][module] = "OK"
        except ImportError:
            status["checks"][module] = "Missing"
    
    return status

