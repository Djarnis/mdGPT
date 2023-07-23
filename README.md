# mdGPT - Mark Down General Purpose Transformer

Translate markdown files using OpenAI ChatGPT, and generate localized copies of each file.

## Installation

### Step 1: Install Poetry

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

### Step 2: Rename .env.tpl to .env

In your project directory, you have a file named .env.tpl which serves as a template for environment variables. To use this file, you should rename it to .env.

On Unix-based systems, use the following command:

```bash
mv .env.tpl .env
```

On Windows, use the following command:

```powershell
rename .env.tpl .env
```

### Step 3: Add OPENAI_API_KEY value to .env

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

### Step 4: Install mdGPT

From the project directory, install mdGPT and its dependencies:

```bash
poetry install
```

This installs mdGPT and all its dependencies, and you can now follow the example below.

## Example

### Build website

The example website ([./example/en](example/en)) was created using the `WEBSITE_BUILDER` option included in the [prompts.yaml](prompts.yaml) file.

```bash
poetry run mdbuild -d example -p prompts -l en
```

Which will create these files in the ./example/en directory:

-   index.md
-   about.md
-   contact.md
-   history.md

## Translate website

To translate the markdown files into Finish (fi) versions, run this command:

```bash
poetry run mdtranslate -p prompts -d example -sl en -tl fi
```

And you should get a `/fi` subdirectory ./example/fi/ containing these files, translated from their original English (en) source:

-   index.md
-   tietoja.md
-   yhteystiedot.md
-   historia.md
