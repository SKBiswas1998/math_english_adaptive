from fastapi import FastAPI, Request, Body
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import pandas as pd
import os
import glob
import json
import random
import time
import uvicorn
from typing import Dict, List, Optional, Any, Union

# Create FastAPI app
app = FastAPI(
    title="Math Quiz App with Anti-Cheating",
    description="An interactive math quiz application with anti-cheating features",
    version="1.0.0"
)

# Add CORS middleware to allow requests from all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Path to the folder containing CSV files
csv_folder_path = r"E:\quiz_app_python\quiz_math"

# Pydantic models for data validation
class TimingLog(BaseModel):
    time: float = Field(..., description="Response time in seconds")
    isCorrect: bool = Field(..., description="Whether the answer was correct")
    question: Optional[str] = Field(None, description="Question ID")
    difficulty: Optional[str] = Field(None, description="Question difficulty")
    timestamp: Optional[str] = Field(None, description="ISO timestamp")

class Question(BaseModel):
    question_id: str
    Subtopic: Optional[str] = None
    Difficulty: str
    Question: str
    Option_A: str = Field(alias="Option A")
    Option_B: str = Field(alias="Option B")
    Option_C: str = Field(alias="Option C")
    Option_D: str = Field(alias="Option D")
    Correct_Answer: str = Field(alias="Correct Answer")
    Explanation: Optional[str] = None
    Source: Optional[str] = None

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True

# Function to load all CSV files from a folder
def load_csv_files_from_folder(folder_path):
    if not os.path.exists(folder_path):
        print(f"No folder found at {folder_path}")
        return pd.DataFrame()
    
    # Get all CSV files in the folder
    csv_files = glob.glob(os.path.join(folder_path, "*.csv"))
    
    if not csv_files:
        print(f"No CSV files found in folder: {folder_path}")
        return pd.DataFrame()
    
    print(f"Found {len(csv_files)} CSV files in folder: {folder_path}")
    
    # List to hold all dataframes
    all_dfs = []
    
    # Load each CSV file
    for file_path in csv_files:
        try:
            # Try reading with default encoding
            df = pd.read_csv(file_path)
            
            # Process the dataframe
            df = process_csv_dataframe(df, os.path.basename(file_path))
            
            # Add to the list
            all_dfs.append(df)
            
        except UnicodeDecodeError:
            # If encoding issue, try with utf-8
            try:
                df = pd.read_csv(file_path, encoding='utf-8')
                df = process_csv_dataframe(df, os.path.basename(file_path))
                all_dfs.append(df)
            except Exception as e:
                print(f"Error loading file {os.path.basename(file_path)}: {str(e)}")
        except Exception as e:
            print(f"Error loading file {os.path.basename(file_path)}: {str(e)}")
    
    # Combine all dataframes
    if all_dfs:
        combined_df = pd.concat(all_dfs, ignore_index=True)
        print(f"Total questions: {len(combined_df)}")
        return combined_df
    else:
        print("No valid CSV files could be loaded.")
        return pd.DataFrame()

# Function to process a CSV dataframe
def process_csv_dataframe(df, filename):
    print(f"Processing: {filename}")
    
    # Ensure expected columns exist
    expected_columns = ['Subtopic', 'Difficulty', 'Question', 'Option A', 'Option B', 
                       'Option C', 'Option D', 'Correct Answer', 'Explanation']
    missing_columns = [col for col in expected_columns if col not in df.columns]
    if missing_columns:
        print(f"Warning: Missing columns {missing_columns} in file {filename}. Available columns: {df.columns.tolist()}")
    
    # Add source filename
    df['Source'] = filename
    
    # Ensure the 'Difficulty' column exists and normalize its values
    if 'Difficulty' in df.columns:
        # Convert to string and strip whitespace
        df['Difficulty'] = df['Difficulty'].astype(str).str.strip()
        
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
        df['Difficulty'] = df['Difficulty'].apply(map_difficulty)
    else:
        # If no difficulty column, assign 'Medium' as default
        df['Difficulty'] = 'Medium'
    
    # Preprocess the 'Correct Answer' column to ensure consistency
    if 'Correct Answer' in df.columns:
        # Convert to string, strip whitespace, remove newlines and special characters, take first character, and convert to uppercase
        df['Correct Answer'] = df['Correct Answer'].astype(str).str.strip().str.replace(r'[\r\n\t\s]+', '', regex=True).str[0].str.upper()
        # Log the processed values for debugging
        print(f"Sample Correct Answer values from {filename} (first character only):", df['Correct Answer'].head().tolist())
    else:
        print(f"Warning: 'Correct Answer' column not found in file {filename}. Available columns:", df.columns.tolist())
    
    # Add unique IDs to each question for tracking
    start_id = 0  # This will be adjusted when combining dataframes
    df['question_id'] = [f"q{start_id + i}" for i in range(len(df))]
    
    print(f"Processed {len(df)} questions from {filename}")
    return df

# Load questions from all CSV files in the folder
all_questions = load_csv_files_from_folder(csv_folder_path)

# Convert DataFrame to list of dictionaries for JSON serialization
questions_list = all_questions.to_dict(orient='records') if not all_questions.empty else []

# Create the HTML template for the main page
# Replace the last section of your code with this:

# Create the HTML template for the main page
@app.get("/", response_class=HTMLResponse)
async def index():
    html_template = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Math Quiz App with Anti-Cheating</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #121212;
            color: #e0e0e0;
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
            background-color: #2a2a2a;
            border-radius: 5px;
            cursor: pointer;
            color: #e0e0e0;
            transition: background-color 0.2s;
        }
        .option:hover {
            background-color: #3a3a3a;
        }
        .option input {
            margin-right: 10px;
        }
        .selected {
            background-color: #445577;
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
        .progress-bar-container {
            width: 100%;
            height: 10px;
            background-color: #2a2a2a;
            border-radius: 5px;
            margin: 10px 0;
        }
        .progress-bar {
            height: 100%;
            border-radius: 5px;
            transition: width 0.3s;
        }
        .cheat-bar {
            background-color: #dc3545;
        }
        .cheat-score {
            margin-left: 5px;
            font-size: 0.9em;
            color: #dc3545;
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
        
        <div class="cheating-detection">
            <div class="progress-bar-container">
                <div id="cheat-indicator" class="progress-bar cheat-bar" style="width: 0%;"></div>
            </div>
            <div style="display: flex; justify-content: space-between;">
                <span>Integrity Score</span>
                <span id="cheat-score" class="cheat-score">100%</span>
            </div>
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
        
        // Anti-cheating variables
        let questionStartTime = 0;
        let cheatScore = 0; // 0-100 scale (0 = no cheating detected, 100 = definitely cheating)
        let responseTimeHistory = [];
        const IDEAL_RESPONSE_TIME = 15; // seconds
        const MAX_ACCEPTABLE_TIME = 60; // seconds
        
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
        const cheatIndicator = document.getElementById('cheat-indicator');
        const cheatScoreDisplay = document.getElementById('cheat-score');

        // Anti-cheating functions
        function startQuestionTimer() {
            questionStartTime = Date.now();
        }
        
        function calculateCheatProbability(responseTime) {
            // Calculate probability based on response time
            if (responseTime <= IDEAL_RESPONSE_TIME) {
                // If answered within ideal time, no cheating suspected
                return 0;
            } else if (responseTime >= MAX_ACCEPTABLE_TIME) {
                // If answer takes too long, high probability of cheating
                return 100;
            } else {
                // Linear increase in probability between ideal and max time
                const timeRange = MAX_ACCEPTABLE_TIME - IDEAL_RESPONSE_TIME;
                const excessTime = responseTime - IDEAL_RESPONSE_TIME;
                return Math.round((excessTime / timeRange) * 100);
            }
        }
        
        function updateCheatScore(newProbability) {
            // Update the overall cheat score with weighted average
            // Give more weight to higher probabilities
            if (newProbability > cheatScore) {
                cheatScore = Math.round(cheatScore * 0.7 + newProbability * 0.3);
            } else {
                cheatScore = Math.round(cheatScore * 0.9 + newProbability * 0.1);
            }
            
            // Ensure it stays in 0-100 range
            cheatScore = Math.max(0, Math.min(100, cheatScore));
            
            // Update the visual indicator
            cheatIndicator.style.width = cheatScore + '%';
            
            // Calculate integrity score (inverse of cheat score)
            const integrityScore = 100 - cheatScore;
            cheatScoreDisplay.textContent = integrityScore + '%';
            
            // Change color based on severity
            if (integrityScore >= 80) {
                cheatScoreDisplay.style.color = '#28a745'; // Green
            } else if (integrityScore >= 50) {
                cheatScoreDisplay.style.color = '#ffc107'; // Yellow
            } else {
                cheatScoreDisplay.style.color = '#dc3545'; // Red
            }
        }
        
        function logResponseTime(responseTime, isCorrect) {
            responseTimeHistory.push({
                time: responseTime,
                isCorrect: isCorrect,
                question: currentQuestion ? currentQuestion.question_id : null,
                difficulty: currentDifficulty,
                timestamp: new Date().toISOString()
            });
            
            // In a real app, you might send this to the server for analysis
            console.log(`Response time: ${responseTime.toFixed(1)}s, Correct: ${isCorrect}`);
        }
        
        // Utility function to inspect string characters
        function inspectString(str) {
            const chars = str.split('').map((char, index) => {
                return `Char ${index}: '${char}' (code: ${char.charCodeAt(0)})`;
            });
            return chars.join(', ');
        }

        // Fetch questions from server
        async function fetchQuestions() {
            try {
                const response = await fetch('/api/questions');
                const data = await response.json();
                questions = data;
                loadNextQuestion();
            } catch (error) {
                console.error('Error fetching questions:', error);
                questionText.innerHTML = '<h3>Error: Could not load questions.</h3>';
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
                questionText.innerHTML = '<h3>Error: No questions available</h3>';
                optionsContainer.innerHTML = '';
                submitBtn.disabled = true;
                return;
            }

            // Store current question
            currentQuestion = question;

            // Update UI with question
            const subtopic = question.Subtopic || '';
            const questionInfo = subtopic ? `<p><i>Subtopic: ${subtopic}</i></p>` : '';
            questionText.innerHTML = `${questionInfo}<h3>${question.Question}</h3>`;

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
            
            // Start timing this question (for anti-cheating)
            startQuestionTimer();
        }

        // Handle submit button click
        function handleSubmit() {
            // Calculate response time
            const responseTime = (Date.now() - questionStartTime) / 1000;
            
            // Check if an option was selected
            const selectedOption = document.querySelector('input[name="quiz-option"]:checked');
            if (!selectedOption) {
                feedbackArea.innerHTML = '<div style="color: red;">Please select an answer</div>';
                feedbackBox.classList.remove('hidden');
                return;
            }

            const selectedAnswer = selectedOption.value.trim().toUpperCase();
            const correctAnswerRaw = String(currentQuestion['Correct Answer'] || '');
            // Remove all non-letter characters and normalize
            const correctAnswer = correctAnswerRaw.replace(/[^A-Z]/gi, '').toUpperCase();
            console.log('Raw Correct Answer:', JSON.stringify(correctAnswerRaw));
            console.log('Raw Correct Answer Inspection:', inspectString(correctAnswerRaw));
            console.log('Processed Correct Answer:', correctAnswer);
            console.log('Processed Correct Answer Inspection:', inspectString(correctAnswer));
            console.log('Selected Answer:', selectedAnswer);
            console.log('Selected Answer Inspection:', inspectString(selectedAnswer));
            const isCorrect = selectedAnswer === correctAnswer;

            // Calculate cheat probability based on timing
            const cheatProbability = calculateCheatProbability(responseTime);
            updateCheatScore(cheatProbability);
            
            // Log response time and correctness
            logResponseTime(responseTime, isCorrect);
            
            // Update score and total questions
            totalQuestionsAnswered++;
            currentBatchCount++;

            if (isCorrect) {
                score++;
                // Increase difficulty
                increaseDifficulty();
                // Update status
                statusLabel.innerHTML = '<span style="color: #4cd137;">Status: Correct!</span>';
                
                // Prepare feedback with time information
                let timingFeedback = '';
                if (responseTime <= IDEAL_RESPONSE_TIME) {
                    timingFeedback = `<p>Great speed! You answered in ${responseTime.toFixed(1)} seconds.</p>`;
                } else if (responseTime <= MAX_ACCEPTABLE_TIME) {
                    timingFeedback = `<p>You answered in ${responseTime.toFixed(1)} seconds.</p>`;
                } else {
                    timingFeedback = `<p>You took ${responseTime.toFixed(1)} seconds to answer.</p>`;
                }
                
                // Prepare feedback
                feedbackArea.innerHTML = `
                    <div style="background-color: #2a2a2a; padding: 15px; border-radius: 5px; margin: 10px 0; border: 1px solid #3a3a3a;">
                        <h3 style="color: #4cd137;">Correct!</h3>
                        <p>Well done! You selected the right answer.</p>
                        ${timingFeedback}
                        <p>Moving to a more challenging question...</p>
                        <p>Questions completed in this batch: ${currentBatchCount}/${batchSize}</p>
                    </div>
                `;
            } else {
                // Decrease difficulty
                decreaseDifficulty();
                // Update status
                const correctOptionText = currentQuestion['Option ' + correctAnswer] || 'Not available';
                const explanation = currentQuestion.Explanation || 'No explanation provided';
                statusLabel.innerHTML = `<span style="color: #ff6b6b;">Status: Incorrect (Correct Answer: ${correctAnswer})</span>`;
                
                // Timing feedback
                let timingFeedback = '';
                if (responseTime <= IDEAL_RESPONSE_TIME) {
                    timingFeedback = `<p>You answered quickly in ${responseTime.toFixed(1)} seconds, but incorrectly.</p>`;
                } else {
                    timingFeedback = `<p>You answered in ${responseTime.toFixed(1)} seconds.</p>`;
                }
                
                // Prepare feedback
                feedbackArea.innerHTML = `
                    <div style="background-color: #2a2a2a; padding: 15px; border-radius: 5px; margin: 10px 0; border: 1px solid #3a3a3a;">
                        <h3 style="color: #ff6b6b;">Incorrect</h3>
                        <p>The correct answer is: <strong>${correctAnswer}: ${correctOptionText}</strong></p>
                        ${timingFeedback}
                        <div style="background-color: #333333; padding: 10px; border-left: 4px solid #ff6b6b; border-radius: 0 5px 5px 0; margin-top: 10px;">
                            <h4>Explanation:</h4>
                            <p>${explanation}</p>
                        </div>
                        <p>We'll try an easier question next time.</p>
                        <p>Questions completed in this batch: ${currentBatchCount}/${batchSize}</p>
                    </div>
                `;
            }

            // Update score label
            scoreLabel.textContent = `Score: ${score}/${totalQuestionsAnswered}`;

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
            let integrityMessage = '';
            const integrityScore = 100 - cheatScore;
            
            if (integrityScore >= 80) {
                integrityMessage = `<p style="color: #28a745;">Your integrity score is excellent at ${integrityScore}%!</p>`;
            } else if (integrityScore >= 50) {
                integrityMessage = `<p style="color: #ffc107;">Your integrity score is ${integrityScore}%. Try to answer at a natural pace.</p>`;
            } else {
                integrityMessage = `<p style="color: #dc3545;">Your integrity score is low at ${integrityScore}%. Our system has detected unusual timing patterns.</p>`;
            }
            
            const batchHTML = `
                <h3>Batch Completed!</h3>
                <p>You completed ${batchSize} questions with a score of ${score}/${batchSize} (${percentage}%).</p>
                <p>Current difficulty level: ${numericDifficulty} (${currentDifficulty})</p>
                ${integrityMessage}
                <p>Would you like to continue with another batch?</p>
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
            const integrityScore = 100 - cheatScore;
            
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
            
            // Determine integrity message
            let integrityMsg = '';
            if (integrityScore >= 80) {
                integrityMsg = "Your timing patterns show natural learning behaviors.";
            } else if (integrityScore >= 50) {
                integrityMsg = "Your timing patterns were somewhat inconsistent.";
            } else {
                integrityMsg = "Your timing patterns suggest you might be using external resources.";
            }
            
            // Display final results
            finalResults.innerHTML = `
                <h2>Quiz Results</h2>
                <p><b>Final Score:</b> ${score}/${totalQuestionsAnswered} (${percentage}%)</p>
                <p><b>Total Questions Answered:</b> ${totalQuestionsAnswered}</p>
                <p><b>Highest Difficulty Reached:</b> Level ${numericDifficulty} (${currentDifficulty})</p>
                <p><b>Integrity Score:</b> ${integrityScore}%</p>
                <p>${performanceMsg}</p>
                <p>${integrityMsg}</p>
                <p style="margin-top: 20px;">Refresh the page or click Reset Quiz to start a new quiz.</p>
            `;
            
            finalResults.classList.remove('hidden');
            
            // In a real application, you might send the response time data to the server
            // for analysis and recording
            console.log("Response time history:", responseTimeHistory);
        }

        // Reset quiz
        function resetQuiz() {
            currentDifficulty = 'Easy';
            numericDifficulty = 1;
            score = 0;
            totalQuestionsAnswered = 0;
            currentBatchCount = 0;
            cheatScore = 0;
            responseTimeHistory = [];
            
            scoreLabel.textContent = `Score: ${score}/${totalQuestionsAnswered}`;
            difficultyLabel.textContent = `Current Difficulty: Level ${numericDifficulty} (${currentDifficulty})`;
            statusLabel.innerHTML = '<span style="color: white;">Status: Ready</span>';
            cheatIndicator.style.width = '0%';
            cheatScoreDisplay.textContent = '100%';
            cheatScoreDisplay.style.color = '#28a745';
            
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
    return html_template

# API endpoints for the quiz app
@app.get("/api/questions", response_model=List[Dict[str, Any]], tags=["Quiz API"])
async def get_questions():
    """
    Get all available quiz questions.
    
    Returns a list of all questions loaded from CSV files.
    """
    return questions_list

@app.post("/api/log-timing", tags=["Quiz API"])
async def log_timing(timing_data: TimingLog):
    """
    Log response time data for anti-cheating analysis.
    
    This endpoint accepts timing data for a quiz question answer,
    including response time and correctness.
    """
    # In a real application, you would store this in a database
    print(f"Timing log: {timing_data}")
    return {"status": "logged"}

# Run the application using uvicorn
if __name__ == "__main__":
    uvicorn.run("anticheating_fastapi_1:app", host="127.0.0.1", port=2000, reload=True)