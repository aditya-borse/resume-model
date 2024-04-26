from flask import Flask, render_template, request, send_from_directory, url_for
from werkzeug.utils import secure_filename
import os
import PyPDF2
import re
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from gensim.models import Word2Vec
from nltk.tokenize import word_tokenize
import string
import sqlite3
import numpy as np
from gensim.models.doc2vec import Doc2Vec
app = Flask(__name__)
import nltk
nltk.download('stopwords')

# Define the upload folder
UPLOAD_FOLDER = './ENGINEERING/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# corpus = [
#     "This is the first document.",
#     "This document is the second document.",
#     "And this is the third one.",
#     "Is this the first document?"
# ]
model = Doc2Vec.load("doc2vec_resumes.model")

@app.route('/serve_resume/<filename>', methods=["GET","POST"],endpoint='serve_resume')
def serve_resume(filename):
    return send_from_directory('ENGINEERING', filename)

@app.route("/", methods=["POST", "GET"])
def home():
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'file' not in request.files:
            return 'No file part'
        file = request.files['file']
        # If the user does not select a file, the browser might
        # submit an empty file part without a filename.
        if file.filename == '':
            return 'No selected file'
        if file:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            text_file_path = os.path.splitext(file_path)[0] + '.txt'
            process_uploaded_pdf(file_path, text_file_path)
            return 'file uploaded and processed successfully'
    return render_template("home.html")

def process_uploaded_pdf(pdf_path, text_file_path):
    # Convert PDF to text
    extract_text_from_pdf(pdf_path, text_file_path)
    
    # Read the text file
    with open(text_file_path, 'r', encoding='utf-8') as file:
        text = file.read()
    
    # Clean the text (example cleaning function)
    cleaned_text = clean_text(text)
    
    # Print the cleaned text (for demonstration purposes)
    print(cleaned_text)
    
    # Here, you would add the code to prepare the cleaned text for the vector database
def extract_text_from_pdf(pdf_path, text_file_path):
    # Open the PDF file in read-binary mode
    with open(pdf_path, 'rb') as file:
        # Create a PDF reader object using PdfReader
        pdf_reader = PyPDF2.PdfReader(file)
        
        # Initialize an empty string to hold the extracted text
        extracted_text = ""
        
        # Loop through each page in the PDF
        for page in pdf_reader.pages:
            # Extract text from the current page
            page_text = page.extract_text()
            # Append the extracted text to the main string
            extracted_text += page_text
        
        # Open the text file in write mode with utf-8 encoding
        with open(text_file_path, 'w', encoding='utf-8') as text_file:
            # Write the extracted text to the file
            text_file.write(extracted_text)
    
    print(f"Text extracted from {pdf_path} and saved to {text_file_path}")

def clean_text(text):
    # Convert to lowercase
    text = text.lower()
    # Remove punctuation
    text = re.sub(r'[^\w\s]', '', text)
    # Remove stop words
    stop_words = set(stopwords.words('english'))
    text = ' '.join([word for word in text.split() if word not in stop_words])
    # Stem words
    stemmer = PorterStemmer()
    text = ' '.join([stemmer.stem(word) for word in text.split()])
    return text

def preprocess_text(text):
    text = text.translate(str.maketrans('', '', string.punctuation))
    text = text.lower()
    tokens = text.split()
    return tokens

@app.route("/search", methods=["POST", "GET"])
def search():
    
    if request.method == "POST":
        key = request.form.get("key")
        if key:
            # Preprocess the search key
            key_tokens = preprocess_text(key)
            # Infer vector for the search key
            key_vector = model.infer_vector(key_tokens)
            print(2)
            # Connect to the database and fetch resume vectors
            conn = sqlite3.connect('resume_vectors.db')
            c = conn.cursor()
            c.execute("SELECT pdf_file_name, vector FROM resumes")
            resume_data = c.fetchall()
            
            # Calculate similarities
            similarities = []
            for resume_id, resume_vector_bytes in resume_data:
                resume_vector = np.frombuffer(resume_vector_bytes, dtype=np.float32)
                similarity = np.dot(resume_vector, key_vector) / (np.linalg.norm(resume_vector) * np.linalg.norm(key_vector))
                similarities.append((resume_id, similarity))
            
            # Sort by similarity and get top 5
            similarities.sort(key=lambda x: x[1], reverse=True)
            top_pdf_file_names = [x[0] for x in similarities[:5]]
            
            # Return the top matching resumes
            return render_template("search_results.html", top_pdf_file_names=top_pdf_file_names)
        else:
            return "No search key provided."
    print(3)
    return render_template("search.html")




if __name__ == '__main__':
    # Ensure the upload folder exists
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run()
