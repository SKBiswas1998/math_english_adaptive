from flask import Flask, render_template, request, jsonify
import pandas as pd
import glob
import os
import json
import random

app = Flask(__name__)

# Directory containing the CSV files
directory_path = r"E:\quiz_app_python\quiz_questions"

# Function to load and combine all CSV files
def load_all_csv_files(directory_path):
    # Get all CSV files in the directory
    csv_files = glob.glob(os.path.join(directory_path, "*.csv"))
    
    if not csv_files:
        print(f"No CSV files found in {directory_path}")
        return pd.DataFrame()
    
    # Read each CSV file and combine them
    dataframes = []
    
    for file_path in csv_files:
        try:
            # First try with default encoding
            df = pd.read_csv(file_path)
        except UnicodeDecodeError:
            # If there's an encoding issue, try with utf-8
            df = pd.read_csv(file_path, encoding='utf-8')
            
        dataframes.append(df)
        print(f"Loaded: {os.path.basename(file_path)}")
    
    # Combine all dataframes
    combined_df = pd.concat(dataframes, ignore_index=True)
    
    # Ensure the 'Difficulty' column exists and normalize its values
    if 'Difficulty' in combined_df.columns:
        # Convert to string and strip whitespace
        combined_df['Difficulty'] = combined_df['Difficulty'].astype(str).str.strip()
        
        # Map numeric difficulty levels (1-10) to categories
        def map_difficulty(diff_value):
            try:
                # Try to convert to integer
                diff_num = int(diff_value)
                if 1 <= diff_num <= 3:
                    return 'Easy'
                elif 4 <= diff_num <= 7:
                    return 'Medium'
                elif 8 <= diff_num <= 10:
                    return 'Hard'
                else:
                    return 'Medium'  # Default for out of range numbers
            except ValueError:
                # If not a number, map text values
                diff_lower = diff_value.lower()
                if diff_lower in ['easy', '1', '2', '3']:
                    return 'Easy'
                elif diff_lower in ['medium', 'intermediate', '4', '5', '6', '7']:
                    return 'Medium'
                elif diff_lower in ['hard', 'difficult', '8', '9', '10']:
                    return 'Hard'
                else:
                    return 'Medium'  # Default for unknown text
        
        # Apply the mapping function
        combined_df['Difficulty'] = combined_df['Difficulty'].apply(map_difficulty)
    else:
        # If no difficulty column, assign 'Medium' as default
        combined_df['Difficulty'] = 'Medium'
    
    print(f"Combined {len(dataframes)} CSV files, total questions: {len(combined_df)}")
    return combined_df

# Load all questions
all_questions = load_all_csv_files(directory_path)

# Convert DataFrame to list of dictionaries for JSON serialization
questions_list = all_questions.to_dict(orient='records')

# Create index.html template (for the main page)
@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Noun Quiz App</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background-color: #121212;
                color: blue;
                margin: 0;
                padding: 20px;
            }
            #quiz-container {
                max-width: 800px;
                margin: 0 auto;
                background-color: #1a1a1a;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 0 10px rgba(0,0,0,0.5);
            }
            .header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 10px 0;
                border-bottom: 1px solid #444444;
                margin-bottom: 20px;
            }
            .status {
                padding: 5px;
                background-color: #2a2a2a;
                border: 1px solid #444444;
                color: white;
            }
            .question {
                margin-bottom: 20px;
            }
            .options {
                margin-bottom: 20px;
            }
            .option {
                display: block;
                padding: 10px;
                margin: 8px 0;
                background-color: #f5f5f5;
                border-radius: 5px;
                cursor: pointer;
                color: blue;
                transition: background-color 0.2s;
            }
            .option:hover {
                background-color: #e8e8e8;
            }
            .option input {
                margin-right: 10px;
            }
            .selected {
                background-color: #d0d0f0;
            }
            .button {
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-weight: bold;
                margin-right: 10px;
            }
            .primary {
                background-color: #007bff;
                color: white;
            }
            .info {
                background-color: #17a2b8;
                color: white;
            }
            .danger {
                background-color: #dc3545;
                color: white;
            }
            .success {
                background-color: #28a745;
                color: white;
            }
            .feedback {
                padding: 15px;
                border-radius: 5px;
                margin: 10px 0;
                border: 1px solid #3a3a3a;
                background-color: #2a2a2a;
            }
            .hidden {
                display: none;
            }
            .batch-control {
                text-align: center;
                padding: 20px;
                margin-top: 20px;
            }
            .final-results {
                padding: 20px;
                margin-top: 20px;
                background-color: #2a2a2a;
                border-radius: 10px;
                text-align: center;
            }
        </style>
    </head>
    <body>
        <div id="quiz-container">
            <div class="header">
                <div id="difficulty-label">Current Difficulty: Level 1 (Easy)</div>
                <div id="score-label">Score: 0/0</div>
                <div id="status-label" class="status">Status: Ready</div>
                <button id="reset-btn" class="button danger">Reset Quiz</button>
            </div>

            <div id="question-area">
                <div id="question-text" class="question"></div>
                <div id="options" class="options"></div>
                <button id="submit-btn" class="button primary">Submit Answer</button>
            </div>

            <div id="feedback-box" class="hidden">
                <div id="feedback-area" class="feedback"></div>
                <button id="next-btn" class="button info">Next Question</button>
            </div>

            <div id="batch-control-area" class="batch-control hidden">
                <h3>Batch Completed!</h3>
                <p>Would you like to continue with another batch?</p>
                <button id="continue-btn" class="button success">Continue Quiz</button>
                <button id="exit-btn" class="button danger">Quit Quiz</button>
            </div>

            <div id="final-results" class="final-results hidden"></div>
        </div>

        <script>
            // Global variables
            let currentDifficulty = 'Easy';
            let numericDifficulty = 1;
            let score = 0;
            let totalQuestionsAnswered = 0;
            let currentQuestion = null;
            let questions = [];
            let batchSize = 10;
            let currentBatchCount = 0;

            // DOM elements
            const difficultyLabel = document.getElementById('difficulty-label');
            const scoreLabel = document.getElementById('score-label');
            const statusLabel = document.getElementById('status-label');
            const questionText = document.getElementById('question-text');
            const optionsContainer = document.getElementById('options');
            const submitBtn = document.getElementById('submit-btn');
            const nextBtn = document.getElementById('next-btn');
            const resetBtn = document.getElementById('reset-btn');
            const continueBtn = document.getElementById('continue-btn');
            const exitBtn = document.getElementById('exit-btn');
            const feedbackArea = document.getElementById('feedback-area');
            const questionArea = document.getElementById('question-area');
            const feedbackBox = document.getElementById('feedback-box');
            const batchControlArea = document.getElementById('batch-control-area');
            const finalResults = document.getElementById('final-results');

            // Fetch questions from server
            async function fetchQuestions() {
                try {
                    const response = await fetch('/api/questions');
                    const data = await response.json();
                    questions = data;
                    loadNextQuestion();
                } catch (error) {
                    console.error('Error fetching questions:', error);
                    questionText.innerHTML = '<h3 style="color: blue;">Error: Could not load questions.</h3>';
                }
            }

            // Get a random question by difficulty
            function getQuestionByDifficulty(difficulty) {
                const filteredQuestions = questions.filter(q => q.Difficulty === difficulty);
                if (filteredQuestions.length === 0) {
                    return null;
                }
                const randomIndex = Math.floor(Math.random() * filteredQuestions.length);
                return filteredQuestions[randomIndex];
            }

            // Load the next question
            function loadNextQuestion() {
                // Check if batch is complete
                if (currentBatchCount >= batchSize) {
                    showBatchCompletePrompt();
                    return;
                }

                // Hide feedback and show question area
                feedbackBox.classList.add('hidden');
                questionArea.classList.remove('hidden');
                batchControlArea.classList.add('hidden');

                // Get a question for the current difficulty
                let question = getQuestionByDifficulty(currentDifficulty);

                // If no questions available at current difficulty, try others
                if (!question) {
                    const difficulties = ['Easy', 'Medium', 'Hard'];
                    const otherDifficulties = difficulties.filter(d => d !== currentDifficulty);
                    
                    for (const difficulty of otherDifficulties) {
                        question = getQuestionByDifficulty(difficulty);
                        if (question) {
                            currentDifficulty = difficulty;
                            if (difficulty === 'Easy') {
                                numericDifficulty = 2;
                            } else if (difficulty === 'Medium') {
                                numericDifficulty = 5;
                            } else {
                                numericDifficulty = 9;
                            }
                            break;
                        }
                    }
                }

                // If still no question found
                if (!question) {
                    questionText.innerHTML = '<h3 style="color: blue;">Error: No questions available</h3>';
                    optionsContainer.innerHTML = '';
                    submitBtn.disabled = true;
                    return;
                }

                // Store current question
                currentQuestion = question;

                // Update UI with question
                const subtopic = question.Subtopic || '';
                const questionInfo = subtopic ? `<p style="color: blue;"><i>Subtopic: ${subtopic}</i></p>` : '';
                questionText.innerHTML = `${questionInfo}<h3 style="color: blue;">${question.Question}</h3>`;

                // Create options
                optionsContainer.innerHTML = '';
                ['A', 'B', 'C', 'D'].forEach(letter => {
                    const option = document.createElement('label');
                    option.className = 'option';
                    option.innerHTML = `
                        <input type="radio" name="quiz-option" value="${letter}">
                        ${letter}: ${question['Option ' + letter]}
                    `;
                    optionsContainer.appendChild(option);
                });

                // Add click event to options for styling
                document.querySelectorAll('.option').forEach(option => {
                    option.addEventListener('click', function() {
                        document.querySelectorAll('.option').forEach(opt => opt.classList.remove('selected'));
                        this.classList.add('selected');
                    });
                });

                // Update difficulty label
                difficultyLabel.textContent = `Current Difficulty: Level ${numericDifficulty} (${currentDifficulty})`;

                // Reset status
                statusLabel.innerHTML = '<span style="color: white;">Status: Ready</span>';

                // Enable submit button
                submitBtn.disabled = false;
            }

            // Handle submit button click
            function handleSubmit() {
                // Check if an option was selected
                const selectedOption = document.querySelector('input[name="quiz-option"]:checked');
                if (!selectedOption) {
                    feedbackArea.innerHTML = '<div style="color: red;">Please select an answer</div>';
                    feedbackBox.classList.remove('hidden');
                    return;
                }

                const selectedAnswer = selectedOption.value;
                const correctAnswer = currentQuestion['Correct Answer'];
                const isCorrect = selectedAnswer === correctAnswer;

                // Update score and total questions
                totalQuestionsAnswered++;
                currentBatchCount++;

                if (isCorrect) {
                    score++;
                    // Increase difficulty
                    increaseDifficulty();
                    // Update status
                    statusLabel.innerHTML = '<span style="color: #4cd137;">Status: Correct!</span>';
                } else {
                    // Decrease difficulty
                    decreaseDifficulty();
                    // Update status
                    statusLabel.innerHTML = `<span style="color: #ff6b6b;">Status: Incorrect (Correct Answer: ${correctAnswer})</span>`;
                }

                // Update score label
                scoreLabel.textContent = `Score: ${score}/${totalQuestionsAnswered}`;

                // Prepare feedback
                if (isCorrect) {
                    feedbackArea.innerHTML = `
                        <div style="background-color: #2a2a2a; padding: 15px; border-radius: 5px; margin: 10px 0; border: 1px solid #3a3a3a;">
                            <h3 style="color: blue;">Correct!</h3>
                            <p style="color: blue;">Well done! You selected the right answer.</p>
                            <p style="color: blue;">Moving to a more challenging question...</p>
                            <p style="color: blue;">Questions completed in this batch: ${currentBatchCount}/${batchSize}</p>
                        </div>
                    `;
                } else {
                    const correctOptionText = currentQuestion['Option ' + correctAnswer];
                    const explanation = currentQuestion.Explanation;
                    
                    feedbackArea.innerHTML = `
                        <div style="background-color: #2a2a2a; padding: 15px; border-radius: 5px; margin: 10px 0; border: 1px solid #3a3a3a;">
                            <h3 style="color: blue;">Incorrect</h3>
                            <p style="color: blue;">The correct answer is: <strong>${correctAnswer}: ${correctOptionText}</strong></p>
                            <div style="background-color: #333333; padding: 10px; border-left: 4px solid blue; border-radius: 0 5px 5px 0; margin-top: 10px;">
                                <h4 style="color: blue;">Explanation:</h4>
                                <p style="color: blue;">${explanation}</p>
                            </div>
                            <p style="color: blue;">We'll try an easier question next time.</p>
                            <p style="color: blue;">Questions completed in this batch: ${currentBatchCount}/${batchSize}</p>
                        </div>
                    `;
                }

                // Update UI
                questionArea.classList.add('hidden');
                feedbackBox.classList.remove('hidden');
            }

            // Show batch complete prompt
            function showBatchCompletePrompt() {
                questionArea.classList.add('hidden');
                feedbackBox.classList.add('hidden');
                
                // Show batch statistics
                const percentage = (score / batchSize * 100).toFixed(1);
                const batchHTML = `
                    <h3 style="color: blue;">Batch Completed!</h3>
                    <p style="color: blue;">You completed ${batchSize} questions with a score of ${score}/${batchSize} (${percentage}%).</p>
                    <p style="color: blue;">Current difficulty level: ${numericDifficulty} (${currentDifficulty})</p>
                    <p style="color: blue;">Would you like to continue with another batch?</p>
                `;
                
                document.querySelector('#batch-control-area h3').outerHTML = batchHTML;
                batchControlArea.classList.remove('hidden');
            }

            // Continue quiz with new batch
            function continueQuiz() {
                currentBatchCount = 0;
                batchControlArea.classList.add('hidden');
                loadNextQuestion();
            }

            // End quiz and show results
            function endQuiz() {
                // Hide all other UI elements
                questionArea.classList.add('hidden');
                feedbackBox.classList.add('hidden');
                batchControlArea.classList.add('hidden');
                
                // Calculate percentage score
                const percentage = (score / totalQuestionsAnswered * 100).toFixed(1);
                
                // Determine performance message
                let performanceMsg = '';
                if (percentage >= 90) {
                    performanceMsg = "Excellent work! You've mastered these questions!";
                } else if (percentage >= 70) {
                    performanceMsg = "Good job! You have a solid understanding.";
                } else if (percentage >= 50) {
                    performanceMsg = "Nice effort! Keep practicing to improve.";
                } else {
                    performanceMsg = "Keep practicing! You'll get better with time.";
                }
                
                // Display final results
                finalResults.innerHTML = `
                    <h2 style="color: blue;">Quiz Results</h2>
                    <p style="color: blue;"><b>Final Score:</b> ${score}/${totalQuestionsAnswered} (${percentage}%)</p>
                    <p style="color: blue;"><b>Total Questions Answered:</b> ${totalQuestionsAnswered}</p>
                    <p style="color: blue;"><b>Highest Difficulty Reached:</b> Level ${numericDifficulty} (${currentDifficulty})</p>
                    <p style="color: blue;">${performanceMsg}</p>
                    <p style="color: blue; margin-top: 20px;">Refresh the page or click Reset Quiz to start a new quiz.</p>
                `;
                
                finalResults.classList.remove('hidden');
            }

            // Reset quiz
            function resetQuiz() {
                currentDifficulty = 'Easy';
                numericDifficulty = 1;
                score = 0;
                totalQuestionsAnswered = 0;
                currentBatchCount = 0;
                
                scoreLabel.textContent = `Score: ${score}/${totalQuestionsAnswered}`;
                difficultyLabel.textContent = `Current Difficulty: Level ${numericDifficulty} (${currentDifficulty})`;
                statusLabel.innerHTML = '<span style="color: white;">Status: Ready</span>';
                
                feedbackBox.classList.add('hidden');
                batchControlArea.classList.add('hidden');
                finalResults.classList.add('hidden');
                
                loadNextQuestion();
            }

            // Increase difficulty
            function increaseDifficulty() {
                numericDifficulty = Math.min(10, numericDifficulty + 1);
                
                if (numericDifficulty <= 3) {
                    currentDifficulty = 'Easy';
                } else if (numericDifficulty <= 7) {
                    currentDifficulty = 'Medium';
                } else {
                    currentDifficulty = 'Hard';
                }
            }

            // Decrease difficulty
            function decreaseDifficulty() {
                numericDifficulty = Math.max(1, numericDifficulty - 1);
                
                if (numericDifficulty <= 3) {
                    currentDifficulty = 'Easy';
                } else if (numericDifficulty <= 7) {
                    currentDifficulty = 'Medium';
                } else {
                    currentDifficulty = 'Hard';
                }
            }

            // Event listeners
            submitBtn.addEventListener('click', handleSubmit);
            nextBtn.addEventListener('click', loadNextQuestion);
            resetBtn.addEventListener('click', resetQuiz);
            continueBtn.addEventListener('click', continueQuiz);
            exitBtn.addEventListener('click', endQuiz);

            // Initialize the app
            fetchQuestions();
        </script>
    </body>
    </html>
    '''

# API endpoint to get questions
@app.route('/api/questions')
def get_questions():
    return jsonify(questions_list)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
