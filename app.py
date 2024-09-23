from flask import Flask, render_template_string, request, render_template, session, Response
import json
import random
import ast
import os
from create_questions import create_questions, load_word_list

app = Flask(__name__)

app.config['TEMPLATES_AUTO_RELOAD'] = True
app.secret_key = 'your_local_secret_key_here'


# Load the quiz data
with open("all_quiz_data.json", "r") as f:
    all_quiz_data = json.load(f)

@app.route('/')
def index():
    session['score'] = 0
    session['total_questions'] = 0
    return render_template("index.html")

@app.route("/get-question")
def get_question():
    question = random.choice(all_quiz_data)
    session['total_questions'] += 1
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
    
    if is_correct:
        session['score'] += 1
    
    score_percentage = (session['score'] / session['total_questions']) * 100
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
        <div class="mt-4 p-4 bg-gray-100 dark:bg-gray-800 rounded-lg shadow-inner">
            <h3 class="text-lg font-semibold mb-2">Your Score</h3>
            <div class="flex items-center justify-between">
                <div class="text-3xl font-bold {{ 'text-green-500' if score_percentage >= 70 else 'text-yellow-500' if score_percentage >= 40 else 'text-red-500' }}">
                    {{ "%d%%" | format(score_percentage) }}
                </div>
                <div class="text-sm text-gray-600 dark:text-gray-400">
                    {{ session['score'] }} / {{ session['total_questions'] }} correct
                </div>
            </div>
            <div class="mt-2 bg-gray-200 dark:bg-gray-700 rounded-full h-4 overflow-hidden">
                <div class="h-full {{ 'bg-green-500' if score_percentage >= 70 else 'bg-yellow-500' if score_percentage >= 40 else 'bg-red-500' }}" style="width: {{ score_percentage }}%;"></div>
            </div>
        </div>
        <button hx-get="/get-question" 
                hx-target="#quiz-container" 
                class="mt-4 bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded">
            Next Question
        </button>
    </div>
        """,
        is_correct=is_correct,
        result_message=result_message,
        score_percentage=score_percentage,
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
    if 'filepath' not in request.form:
        return 'No filepath provided', 400
    
    filepath = request.form['filepath']
    
    if not filepath:
        return 'No filepath entered', 400
    
    if os.path.isfile(filepath) and allowed_file(filepath):
        # Store the filepath in the session or a global variable
        # so it can be accessed by hfsearch function
        session['current_filepath'] = filepath
        return f"Successfully picked file: {filepath}", 200
    else:
        return 'Invalid filepath or file type', 400

@app.route('/hfsearch', methods=['POST'])
def hfsearch():
    repo = request.form.get('repo')
    filename = request.form.get('filename')
    do_validation = request.form.get('validation') == 'true'
    
    word_list_filepath = session.get('current_filepath')

    def generate():
        word_list = load_word_list(word_list_filepath)
        total_words = len(word_list)
        
        def progress_callback(i, question):
            progress = int((i + 1) / total_words * 100)
            yield f"data: {json.dumps({'progress': progress, 'question': question})}\n\n"

        yield from create_questions(repo, filename, word_list, validate=do_validation, progress_callback=progress_callback)

        yield f"data: {json.dumps({'progress': 100})}\n\n"

    return Response(generate(), mimetype='text/event-stream')



if __name__ == "__main__":
    app.run(debug=True)
