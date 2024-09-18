from flask import Flask, render_template_string, request, render_template
import json
import random
import ast
import os
from werkzeug.utils import secure_filename


app = Flask(__name__)

app.config['TEMPLATES_AUTO_RELOAD'] = True

# Load the quiz data
with open("all_quiz_data.json", "r") as f:
    all_quiz_data = json.load(f)

@app.route('/')
def index():
    return render_template("index.html")

@app.route("/get-question")
def get_question():
    question = random.choice(all_quiz_data)
    return render_template_string(
        """
    <div class="p-4">
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
            <button class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded dark:bg-blue-600 dark:hover:bg-blue-400">
                Submit Answer
            </button>
        </form>
    </div>
    """,
        question=question,
        enumerate=enumerate,
    )


@app.route("/check-answer", methods=["POST"])
def check_answer():
    user_answer = int(request.form["answer"])
    correct_answer_index = int(request.form["correct_answer"])
    choices_str = request.form["choices"]

    try:
        choices = ast.literal_eval(choices_str)
    except (ValueError, SyntaxError) as e:
        return f"Error parsing choices: {e}", 400

    if not isinstance(choices, list) or len(choices) <= correct_answer_index:
        return "Invalid choices data", 400

    correct_choice = choices[correct_answer_index]
    is_correct = user_answer == correct_answer_index
    result_message = (
        "Correct!"
        if is_correct
        else f'Incorrect. The correct answer was "{correct_choice}".'
    )

    return render_template_string(
        """
    <div class="p-4">
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
    """,
        is_correct=is_correct,
        result_message=result_message,
    )

UPLOAD_FOLDER = 'uploads'

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

ALLOWED_EXTENSIONS = {'txt', 'csv'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file part', 400
    
    files = request.files.getlist('file')
    
    if not files or files[0].filename == '':
        return 'No selected file', 400
    
    successful_uploads = []
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            successful_uploads.append(filename)
    
    if successful_uploads:
        print(f"item uploaded {app.config['UPLOAD_FOLDER']}")
        return f"Successfully uploaded: {', '.join(successful_uploads)}", 200
    else:
        return 'No valid files were uploaded', 400

@app.route('/hfsearch', methods=['POST'])
def hfsearch():
    repo = request.form.get('repo')
    filename = request.form.get('filename')
    
    # Process the input values here
    # For now, we'll just print them
    print(f"Repo: {repo}")
    print(f"Filename: {filename}")




if __name__ == "__main__":
    app.run(debug=True)
