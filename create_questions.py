# Import necessary libraries
from llama_cpp import Llama
from pydantic import BaseModel
from typing import List, Optional
from lmformatenforcer import JsonSchemaParser
from lmformatenforcer.integrations.llamacpp import (
    build_llamacpp_logits_processor,
    build_token_enforcer_tokenizer_data,
)
from llama_cpp import LogitsProcessorList
import json
import random

def load_word_list(word_list_fp):
    words = []
    with open(word_list_fp, 'r') as file:
        for line in file:
            word = line.strip()
            if word:  # Ignore empty lines
                words.append(word)
    return words

# Function to save quiz questions to a JSON file
def save_to_json_file(filename: str, data: List[dict]):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)


# Function to load existing data from a JSON file
def load_from_json_file(filename: str) -> List[dict]:
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


# Load the Llama model using from_pretrained method
def load_model(
    repo_id="QuantFactory/Phi-3.5-mini-instruct-GGUF",
    filename="Phi-3.5-mini-instruct.Q5_K_M.gguf",
):
    llm = Llama.from_pretrained(
        repo_id=repo_id,
        filename=filename,
        use_mlock=True,
        n_gpu_layers=-1,
    )
    return llm


# Define the Pydantic schema for a quiz question
class QuizQuestion(BaseModel):
    word: str
    question: str
    choices: List[str]
    correct_answer: int


class ValidationResult(BaseModel):
    is_correct: bool


# Generate prompt with system message and user message
DEFAULT_SYSTEM_PROMPT = """\
You are a helpful assistant. Always answer as helpfully as possible, while being safe. Your answers should be clear and concise. Please ensure that your responses are accurate and adhere to the given format.
"""


def get_prompt(word: str, system_prompt: str = DEFAULT_SYSTEM_PROMPT) -> str:
    return f"<|system|>\n{system_prompt}<|end|>\n<|user|>\nGenerate a vocabulary quiz question for the word '{word}' in the following format:\n\n1. Formulate a question about the word's meaning.\n2. Provide four possible definitions as multiple-choice options.\n3. Ensure that the 'choices' array contains exactly four strings.\n4. Do not include indices, correctness indicators, or any additional text in the choices.\n5. Indicate the index (0-3) of the correct answer but do not include this index of possible responses.\n\You MUST with a JSON object that follows this schema:\n\n{QuizQuestion.schema_json()}\n<|end|>"


def get_prompt_validator(
    word: str, question: str, answer: str, system_prompt: str = DEFAULT_SYSTEM_PROMPT
) -> str:
    return f"""<|system|>
{system_prompt}
<|end|>
<|user|>
Please verify if the following answer is correct for the given word and question:

Word: {word}
Question: {question}
Provided Answer: {answer}

Respond with a JSON object that follows this schema:

{ValidationResult.schema_json()}

Set 'is_correct' to true if the provided answer is correct for the given word and question, and false otherwise.
<|end|>"""


# Function to generate quiz question with JSON schema enforcement
def llamacpp_with_schema_enforcement(
    prompt: str, llm, tokenizer_data, schema_enforcer: Optional[JsonSchemaParser]
) -> str:
    logits_processors = LogitsProcessorList(
        [build_llamacpp_logits_processor(tokenizer_data, schema_enforcer)]
    )
    output = llm(prompt, logits_processor=logits_processors, max_tokens=2048)
    text = output["choices"][0]["text"]
    return text


def generate_with_varied_params(
    llm: Llama, prompt: str, tokenizer_data, schema_enforcer: JsonSchemaParser
) -> str:
    # Randomly vary parameters
    temperature = random.uniform(0.0, 0.5)
    top_p = random.uniform(0.9, 1.0)
    top_k = random.randint(40, 60)

    logits_processors = LogitsProcessorList(
        [build_llamacpp_logits_processor(tokenizer_data, schema_enforcer)]
    )

    output = llm(
        prompt,
        max_tokens=2048,
        temperature=temperature,
        top_p=top_p,
        top_k=top_k,
        logits_processor=logits_processors,
    )

    return output["choices"][0]["text"]


def validate_question(
    quiz_question: dict, llm: Llama, tokenizer_data, schema_enforcer_validator
) -> bool:
    word = quiz_question["word"]
    question_text = quiz_question["question"]
    choices = quiz_question["choices"]
    print(f"choices {choices}")
    correct_answer_index = quiz_question["correct_answer"]

    if not isinstance(choices, list) or len(choices) != 4:
        print(f"Invalid choices for word '{word}': {choices}")
        return False

    correct_answer = choices[correct_answer_index]

    prompt = get_prompt_validator(word, question_text, correct_answer)

    result = llamacpp_with_schema_enforcement(
        prompt, llm, tokenizer_data, schema_enforcer_validator
    )

    print(result)

    try:
        validation_result = ValidationResult.parse_raw(result)
        return validation_result.is_correct
    except json.JSONDecodeError:
        print(f"Failed to parse JSON result for '{word}'.")
        return False
    except Exception as e:
        print(f"Unexpected error during validation for '{word}': {str(e)}")
        return False


def create_questions(repo_id, filename, word_list=None, validate=True, progress_callback=None):
    if word_list is None:
        with open("combined.csv", "r") as f:
            words = f.read().split("\n")
    else:
        words = word_list

    # Load the model
    llm = load_model()

    # Prepare the tokenizer data for the Llama model
    tokenizer_data = build_token_enforcer_tokenizer_data(llm)

    # Set up JSON schema enforcement for the QuizQuestion schema
    schema_enforcer_question = JsonSchemaParser(QuizQuestion.schema())
    schema_enforcer_validator = JsonSchemaParser(ValidationResult.schema())

    # Define the JSON file where all questions will be stored
    json_file = "all_quiz_data.json"

    # Load existing questions
    all_questions = load_from_json_file(json_file)

    done_words = [q["word"] for q in all_questions]

    for i, word in enumerate(words):
        if word in done_words:
            continue

        prompt = get_prompt(word)

        max_attempts = 5
        attempt = 0
        valid_question = False

        while not valid_question and attempt < max_attempts:
            try:
                result = generate_with_varied_params(
                    llm, prompt, tokenizer_data, schema_enforcer_question
                )
                quiz_question = json.loads(result)

                if validate:
                    if validate_question(
                        quiz_question, llm, tokenizer_data, schema_enforcer_validator
                    ):
                        all_questions.append(quiz_question)
                        save_to_json_file(json_file, all_questions)
                        valid_question = True
                        if progress_callback:
                            yield from progress_callback(i, quiz_question)
                    else:
                        print(
                            f"Question validation failed for '{word}'. Attempt {attempt + 1}/{max_attempts}. Regenerating..."
                        )
                else:
                    all_questions.append(quiz_question)
                    save_to_json_file(json_file, all_questions)
                    valid_question = True
                    if progress_callback:
                        yield from progress_callback(i, quiz_question)
            except json.JSONDecodeError:
                print(
                    f"Failed to parse JSON result for '{word}'. Attempt {attempt + 1}/{max_attempts}. Regenerating..."
                )

            attempt += 1

        if not valid_question:
            print(
                f"Failed to generate a valid question for '{word}' after {max_attempts} attempts. Moving to next word."
            )
