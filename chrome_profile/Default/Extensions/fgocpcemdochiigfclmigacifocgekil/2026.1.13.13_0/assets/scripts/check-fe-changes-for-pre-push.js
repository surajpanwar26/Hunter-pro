/**
 * Script to check if frontend files are being pushed.
 * Returns exit code 0 if FE files changed (tests should run), 1 if not.
 */
const { execSync } = require('child_process');

const FE_PATTERNS = ['*.ts',  '*.js'];
const EXCLUDE_PATTERNS = ['scripts/*', '*.config.js', '*.conf.js'];

function exec(cmd) {
    try {
        execSync(cmd, { encoding: 'utf-8', stdio: ['pipe', 'pipe', 'pipe'] });
        return true;
    } catch {
        return false;
    }
}

function execOutput(cmd) {
    try {
        return execSync(cmd, { encoding: 'utf-8', stdio: ['pipe', 'pipe', 'pipe'] }).trim();
    } catch {
        return null;
    }
}

function hasFEChanges() {
    // Build exclude args
    const excludeArgs = EXCLUDE_PATTERNS.map(p => `':!${p}'`).join(' ');

    // 1. Check staged files (pre-commit scenario)
    for (const pattern of FE_PATTERNS) {
        // git diff --cached --quiet returns exit 1 if there ARE changes
        const hasChanges = !exec(`git diff --cached --quiet -- "${pattern}" ${excludeArgs}`);
        if (hasChanges) {
            const files = execOutput(`git diff --cached --name-only -- "${pattern}"`);
            if (files) {
                const filtered = files.split('\n').filter(f =>
                    f && !EXCLUDE_PATTERNS.some(ex => f.includes(ex.replace('*', '')))
                );
                if (filtered.length > 0) {
                    console.log(`Found ${filtered.length} staged FE files:`);
                    filtered.forEach(f => console.log(`  ${f}`));
                    return true;
                }
            }
        }
    }

    // 2. Check unpushed commits (pre-push scenario)
    const upstream = execOutput('git rev-parse --abbrev-ref @{u}');
    if (upstream) {
        for (const pattern of FE_PATTERNS) {
            const files = execOutput(`git diff --name-only @{u}..HEAD -- "${pattern}"`);
            if (files && files.length > 0) {
                const filtered = files.split('\n').filter(f =>
                    f && !EXCLUDE_PATTERNS.some(ex => f.includes(ex.replace('*', '')))
                );
                if (filtered.length > 0) {
                    console.log(`Found ${filtered.length} unpushed FE files`);
                    return true;
                }
            }
        }
    }

    // 3. Check all commits on branch vs common bases
    const bases = ['origin/feature/glide-tool'];
    for (const base of bases) {
        const mergeBase = execOutput(`git merge-base ${base} HEAD`);
        if (mergeBase) {
            for (const pattern of FE_PATTERNS) {
                const files = execOutput(`git diff --name-only ${mergeBase}..HEAD -- "${pattern}"`);
                if (files && files.length > 0) {
                    const filtered = files.split('\n').filter(f =>
                        f && !EXCLUDE_PATTERNS.some(ex => f.includes(ex.replace('*', '')))
                    );
                    if (filtered.length > 0) {
                        console.log(`Found ${filtered.length} FE files changed since ${base}`);
                        filtered.slice(0, 5).forEach(f => console.log(`  ${f}`));
                        if (filtered.length > 5) console.log(`  ... and ${filtered.length - 5} more`);
                        return true;
                    }
                }
            }
            break; // Found a valid base, no need to try others
        }
    }

    return false;
}

function main() {
    if (hasFEChanges()) {
        console.log('\nFE files changed - tests required.');
        process.exit(42); // Special code: FE changes found, run tests
    } else {
        console.log('No FE files changed, skipping tests.');
        process.exit(0); // No changes, allow push
    }
}

main();
