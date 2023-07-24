# mdGPT - Mark Down General Purpose Transformer

Translate markdown files using OpenAI ChatGPT, and generate localized copies of each file.

## Installation

### Using pip

```bash
pip install mdgpt
```

Set environment variable `OPENAI_API_KEY` or create it in a `.env` file

```bash
export OPENAI_API_KEY=YOUR_API_KEY
```

Download example prompts:

```bash
curl -o example.yaml https://raw.githubusercontent.com/Djarnis/mdGPT/main/prompts.yaml
```

Use the example `WEBSITE_BUILDER` option from the prompts to build some example files;

```bash
mdgpt build example
```

Translate these markdown files into Finish (fi) versions:

```bash
mdgpt translate example --target fi
```

or Danish (da):

```bash
mdgpt translate example --target da
```

or German (de):

```bash
mdgpt translate example --target de
```

Or whatever. Just make sure it is an ISO 639-1 two-letter language code, and all should be fine.

Adjust the `example.yaml` prompts to suit your needs.

#### MODEL

You can change the `MODEL` to any engine supported by OpenAI, change the default temperature, and adjust max tokens.

Default values are:

```yaml
MODEL:
    temperature: 0.2
    engine: gpt-3.5-turbo
    max_tokens: 2048
```

#### WEBSITE_BUILDER

This option is used for building mark down documents, given the example instructions below:

```yaml
WEBSITE_BUILDER:
    title: The AI Markdown Translator
    description: Translate markdown files for websites
    system_prompt: |
        Only reply in valid markdown with frontmatter.
        No explanations. No notes.
        Language: {lang[name]}
        Markdown Document:
        ---
        # Frontmatter attributes:
        title: Title of webpage
        description: Short meta description
        ---
        <!-- markdown content -->
    user_suffix: |
        Respond in valid markdown format including all provided frontmatter attributes.

    steps:
        - prompt: |
              Write the homepage content for the fictive product "The AI Markdown Translator" in {lang[name]} ({lang[code]}).
          destination: index.md
        - prompt: |
              Write the "About Us" page content for a fictive team behind the fictive product "The AI Markdown Translator" in {lang[name]} ({lang[code]}).
          destination: about.md
        - prompt: |
              Write the history for the fictive product "The AI Markdown Translator" in {lang[name]} ({lang[code]}), starting in 2019 with 5 major milestones.
          destination: history.md
```

#### URL_PROMPT

This prompt is used when translating file paths.

#### MARKDOWN_PROMPT

This prompt is used when translating markdown files.

#### ONLY_INDEXES

Optional boolean value, if you only want `index.md` files translated.

```yaml
ONLY_INDEXES: True
```

#### FIELD_KEYS

Optional list of frontmatter keys you want to translate.

Per default, all keys will be translated, but you can define selected ones here.

```yaml
FIELD_KEYS:
    - title
    - description
    - keywords
    - heading
    - teaser
```

---

### Using repo source and Poetry:

#### Step 1: Install Poetry

Poetry is a tool for dependency management and packaging in Python. It allows you to declare the libraries your project depends on and it will manage (install/update) them for you.

On Unix-based systems like Linux and MacOS, you can install Poetry by using the following command in your terminal:

```bash
curl -sSL https://install.python-poetry.org | python -
```

On Windows, you can use PowerShell to install Poetry with the following command:

```powershell
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -
```

You can check if Poetry was installed correctly by running:

```bash
poetry --version
```

#### Step 2: Rename .env.tpl to .env

In your project directory, you have a file named .env.tpl which serves as a template for environment variables. To use this file, you should rename it to .env.

On Unix-based systems, use the following command:

```bash
mv .env.tpl .env
```

On Windows, use the following command:

```powershell
rename .env.tpl .env
```

#### Step 3: Add OPENAI_API_KEY value to .env

Open your .env file in a text editor. You should see a line that looks something like this:

```bash
OPENAI_API_KEY=
```

After the equal sign, add your OpenAI API key in quotes. It should look something like this:

```bash
OPENAI_API_KEY="your-api-key-goes-here"
```

Save the .env file and close it.

_Please note:_

-   Make sure to replace "your-api-key-goes-here" with your actual OpenAI API key.
-   Do not share your .env file or post it online, as it contains sensitive information.

#### Step 4: Install mdGPT

From the project directory, install mdGPT and its dependencies:

```bash
poetry install
```

This installs mdGPT and all its dependencies, and you can now follow the example below.

## Example

### Build Markdown files

The example website ([./example/en](example/en)) was created using the `WEBSITE_BUILDER` option included in the [prompts.yaml](prompts.yaml) file.

```bash
poetry run mdgpt build example
```

Which will create these files in the ./example/en directory:

-   index.md
-   about.md
-   contact.md
-   history.md

## Translate website

To translate the markdown files into Finish (fi) versions, run this command:

```bash
poetry run mdgot translate example --target fi
```

And you should get a `/fi` subdirectory ./example/fi/ containing these files, translated from their original English (en) source:

-   index.md
-   tietoja.md
-   yhteystiedot.md
-   historia.md
