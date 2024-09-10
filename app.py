from flask import Flask, render_template_string, request, jsonify
import json
import random
import ast

app = Flask(__name__)

# Load the quiz data
with open("all_quiz_data.json", "r") as f:
    all_quiz_data = json.load(f)

@app.route('/')
def index():
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Vocabulary Quiz</title>
        <script src="https://unpkg.com/htmx.org@1.9.6"></script>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-100 p-8">
        <div class="max-w-md mx-auto bg-white rounded-xl shadow-md overflow-hidden md:max-w-2xl p-6">
            <h1 class="text-2xl font-bold mb-4">Vocabulary Quiz</h1>
            <div id="quiz-container"
                 hx-get="/get-question"
                 hx-trigger="load"
                 hx-swap="innerHTML">
                Loading question...
            </div>
        </div>
    </body>
    </html>
    ''')

@app.route('/get-question')
def get_question():
    question = random.choice(all_quiz_data)
    return render_template_string('''
    <div>
        <h2 class="text-xl font-semibold mb-2">{{ question['word'] }}</h2>
        <p class="mb-4">{{ question['question'] }}</p>
        <form hx-post="/check-answer" hx-swap="outerHTML">
            {% for i, choice in enumerate(question['choices']) %}
            <div class="mb-2">
                <input type="radio" id="choice{{ i }}" name="answer" value="{{ i }}" class="mr-2">
                <label for="choice{{ i }}">{{ choice }}</label>
            </div>
            {% endfor %}
            <input type="hidden" name="correct_answer" value="{{ question['correct_answer'] }}">
            <input type="hidden" name="choices" value="{{ question['choices'] }}">
            <button type="submit" class="mt-4 bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
                Submit Answer
            </button>
        </form>
    </div>
    ''', question=question, enumerate=enumerate)

@app.route('/check-answer', methods=['POST'])
def check_answer():
    user_answer = int(request.form['answer'])
    correct_answer_index = int(request.form['correct_answer'])
    choices_str = request.form['choices']  # Get the choices string

    # Manually format the choices string to a proper list
    try:
        choices = ast.literal_eval(choices_str)
    except (ValueError, SyntaxError) as e:
        return f"Error parsing choices: {e}", 400

    # Ensure choices is a list and has the correct length
    if not isinstance(choices, list) or len(choices) <= correct_answer_index:
        return "Invalid choices data", 400

    correct_choice = choices[correct_answer_index]
    is_correct = user_answer == correct_answer_index
    result_message = 'Correct!' if is_correct else f'Incorrect. The correct answer was "{correct_choice}".'

    return render_template_string('''
    <div>
        <h2 class="text-xl font-semibold mb-2">Result</h2>
        <p class="{{ 'text-green-600' if is_correct else 'text-red-600' }}">
            {{ result_message }}
        </p>
        <button hx-get="/get-question" 
                hx-target="#quiz-container" 
                class="mt-4 bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded">
            Next Question
        </button>
    </div>
    ''', is_correct=is_correct, result_message=result_message)

if __name__ == '__main__':
    app.run(debug=True)