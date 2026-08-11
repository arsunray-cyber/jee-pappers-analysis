import streamlit as st
import pymupdf
import re
import os
from pathlib import Path
from typing import List, Dict, Tuple, Optional

# Page configuration
st.set_page_config(
    page_title="JEE Mains Practice Exam",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for exam-like interface
st.markdown("""
<style>
    .question-box {
        background-color: #f8f9fa;
        border-left: 5px solid #0068c9;
        padding: 20px;
        margin: 10px 0;
        border-radius: 5px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .question-text {
        font-size: 18px;
        font-weight: 600;
        color: #1f2937;
        margin-bottom: 15px;
    }
    .option-label {
        font-size: 16px;
        padding: 8px 12px;
        margin: 5px 0;
        border-radius: 4px;
        background-color: white;
        border: 1px solid #e5e7eb;
    }
    .stRadio > label {
        font-weight: 500;
    }
    .exam-header {
        background: linear-gradient(90deg, #0068c9 0%, #004a99 100%);
        color: white;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .timer-box {
        background-color: #fee2e2;
        border: 2px solid #ef4444;
        padding: 10px 20px;
        border-radius: 8px;
        font-weight: bold;
        font-size: 18px;
        text-align: center;
    }
    .nav-button {
        width: 100%;
        margin: 5px 0;
    }
    .answered {
        background-color: #d1fae5 !important;
        border-color: #10b981 !important;
    }
    .not-answered {
        background-color: #fef3c7 !important;
        border-color: #f59e0b !important;
    }
    .correct-answer {
        background-color: #d1fae5;
        border-left: 5px solid #10b981;
    }
    .wrong-answer {
        background-color: #fee2e2;
        border-left: 5px solid #ef4444;
    }
    .score-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 30px;
        border-radius: 15px;
        text-align: center;
        margin: 20px 0;
    }
    .score-number {
        font-size: 48px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


class QuestionParser:
    """Parse JEE Mains PDF papers and extract questions with options"""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.doc = pymupdf.open(pdf_path)
        
    def extract_text(self) -> str:
        """Extract all text from PDF"""
        full_text = ""
        for page in self.doc:
            full_text += page.get_text()
        return full_text
    
    def extract_text_with_structure(self) -> List[Dict]:
        """Extract text with block structure preserved"""
        blocks_data = []
        for page_num, page in enumerate(self.doc):
            blocks = page.get_text('dict')['blocks']
            for block in blocks:
                if block['type'] == 0:  # Text block
                    text_lines = []
                    for line in block.get('lines', []):
                        line_text = ''.join(span['text'] for span in line.get('spans', []))
                        if line_text.strip():
                            text_lines.append(line_text.strip())
                    
                    if text_lines:
                        full_text = ' '.join(text_lines)
                        blocks_data.append({
                            'page': page_num + 1,
                            'bbox': block.get('bbox', []),
                            'text': full_text
                        })
        return blocks_data
    
    def parse_questions(self) -> List[Dict]:
        """Parse questions from extracted text using structured approach"""
        blocks = self.extract_text_with_structure()
        questions = []
        
        current_question = None
        current_options = []
        question_counter = 0
        
        for block in blocks:
            text = block['text']
            
            # Check if this is a question header
            q_match = re.match(r'^Q(\d+)\.\s*(.+)$', text, re.IGNORECASE)
            
            if q_match:
                # Save previous question if exists
                if current_question is not None:
                    questions.append(self._create_question_dict(
                        question_counter, current_question, current_options
                    ))
                
                # Start new question
                question_counter = int(q_match.group(1))
                current_question = q_match.group(2).strip()
                current_options = []
            elif re.match(r'^\(([1-4])\)\s*(.*)$', text):
                # This is an option
                opt_match = re.match(r'^\(([1-4])\)\s*(.*)$', text)
                if opt_match:
                    opt_num = int(opt_match.group(1))
                    opt_text = opt_match.group(2).strip()
                    # Ensure we have enough slots
                    while len(current_options) < opt_num:
                        current_options.append('')
                    current_options[opt_num - 1] = opt_text
            elif current_question and not current_options:
                # Continuation of question text (before options start)
                current_question += ' ' + text
            elif current_question and current_options:
                # Could be continuation of last option
                if len(current_options) > 0:
                    current_options[-1] += ' ' + text
        
        # Don't forget the last question
        if current_question is not None:
            questions.append(self._create_question_dict(
                question_counter, current_question, current_options
            ))
        
        return questions
    
    def _create_question_dict(self, number: int, text: str, options: List[str]) -> Dict:
        """Create a question dictionary with proper formatting"""
        # Clean up text
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Filter valid options
        valid_options = [opt for opt in options if opt and len(opt) > 0]
        
        # Detect subject and type
        subject = self._detect_subject(text)
        question_type = 'MCQ' if len(valid_options) >= 2 else 'Numerical'
        
        # If no valid options, mark as numerical
        if len(valid_options) < 2:
            valid_options = ['Numerical Answer']
        
        return {
            'number': number,
            'text': text,
            'options': valid_options,
            'subject': subject,
            'question_type': question_type
        }
    
    def _extract_options(self, text: str) -> List[str]:
        """Extract multiple choice options from text"""
        options = []
        
        # Pattern 1: Standard (1), (2), (3), (4) format
        simple_pattern = r'\(([1-4])\)\s*([^\(]+?)(?=\([1-4]\)|Q\d+|ANSWER|$)'
        matches = re.findall(simple_pattern, text, re.DOTALL)
        
        if len(matches) >= 2:
            # Create options array based on found option numbers
            options_dict = {}
            for opt_num, opt_text in matches:
                options_dict[int(opt_num)] = opt_text.strip()
            
            # Build ordered list
            for i in range(1, 5):
                if i in options_dict:
                    options.append(options_dict[i])
        
        # Pattern 2: Try extracting by looking for newlines before option markers
        if len(options) < 2:
            lines = text.split('\n')
            current_option = None
            current_text = []
            
            for line in lines:
                opt_match = re.match(r'^\s*\(([1-4])\)\s*(.*)$', line.strip())
                if opt_match:
                    if current_option and current_text:
                        options.append(' '.join(current_text).strip())
                    current_option = int(opt_match.group(1))
                    current_text = [opt_match.group(2).strip()] if opt_match.group(2).strip() else []
                elif current_option is not None:
                    current_text.append(line.strip())
            
            if current_option and current_text:
                options.append(' '.join(current_text).strip())
        
        return [opt for opt in options if opt and len(opt) > 0]
    
    def _clean_question_text(self, text: str, options: List[str]) -> str:
        """Remove options from question text"""
        cleaned = text
        
        # Remove option patterns
        for opt in options:
            if opt:
                cleaned = cleaned.replace(opt, '')
        
        # Remove (1), (2), (3), (4) markers
        cleaned = re.sub(r'\([1-4]\)', '', cleaned)
        
        # Clean up extra whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        return cleaned.strip()
    
    def _detect_subject(self, text: str) -> str:
        """Detect subject based on question content"""
        text_lower = text.lower()
        
        # Mathematics keywords
        math_keywords = ['equation', 'triangle', 'circle', 'parabola', 'function', 
                        'integral', 'derivative', 'matrix', 'probability', 'angle',
                        'vector', 'line', 'plane', 'coordinate', 'tan', 'sin', 'cos']
        
        # Physics keywords
        physics_keywords = ['velocity', 'acceleration', 'force', 'energy', 'magnetic',
                          'electric', 'field', 'particle', 'motion', 'wave', 'light',
                          'resistance', 'current', 'voltage', 'temperature', 'pressure']
        
        # Chemistry keywords
        chem_keywords = ['reaction', 'compound', 'molecule', 'acid', 'base', 'ion',
                        'bond', 'electron', 'atom', 'solution', 'oxidation', 'reduction',
                        'organic', 'iupac', 'molar', 'gas', 'catalyst']
        
        math_count = sum(1 for kw in math_keywords if kw in text_lower)
        physics_count = sum(1 for kw in physics_keywords if kw in text_lower)
        chem_count = sum(1 for kw in chem_keywords if kw in text_lower)
        
        max_count = max(math_count, physics_count, chem_count)
        
        if max_count == 0:
            return "General"
        elif math_count == max_count:
            return "Mathematics"
        elif physics_count == max_count:
            return "Physics"
        else:
            return "Chemistry"
    
    def extract_answer_key(self) -> Dict[int, int]:
        """Extract answer key from PDF"""
        text = self.extract_text()
        answer_key = {}
        
        # Find answer key section
        answer_section = re.search(r'ANSWER\s*KEY.*?(?=\n\n|$)', text, re.IGNORECASE | re.DOTALL)
        if not answer_section:
            # Try another pattern
            answer_section = re.search(r'(\d+\.\s*\(\d+\))+', text)
        
        if answer_section:
            answer_text = answer_section.group(0)
            # Extract question number and answer
            matches = re.findall(r'(\d+)\.\s*\((\d+)\)', answer_text)
            for q_num, ans in matches:
                answer_key[int(q_num)] = int(ans)
        
        return answer_key


def get_pdf_files(directory: str) -> List[str]:
    """Get list of PDF files in directory"""
    pdf_dir = Path(directory)
    if pdf_dir.exists():
        return sorted([str(f) for f in pdf_dir.glob("*.pdf")])
    return []


def initialize_session_state():
    """Initialize session state variables"""
    if 'current_paper' not in st.session_state:
        st.session_state.current_paper = None
    if 'questions' not in st.session_state:
        st.session_state.questions = []
    if 'answers' not in st.session_state:
        st.session_state.answers = {}
    if 'current_question' not in st.session_state:
        st.session_state.current_question = 0
    if 'paper_name' not in st.session_state:
        st.session_state.paper_name = ""
    if 'answer_key' not in st.session_state:
        st.session_state.answer_key = {}
    if 'exam_submitted' not in st.session_state:
        st.session_state.exam_submitted = False


def main():
    st.title("📝 JEE Mains Practice Exam")
    st.markdown("---")
    
    initialize_session_state()
    
    # Sidebar for paper selection
    with st.sidebar:
        st.header("📚 Select Paper")
        
        # Default papers directory
        papers_dir = "/workspace/papers-2025"
        
        # Check if directory exists, if not use current directory
        if not os.path.exists(papers_dir):
            papers_dir = "/workspace"
        
        pdf_files = get_pdf_files(papers_dir)
        
        if pdf_files:
            paper_options = [os.path.basename(f) for f in pdf_files]
            selected_paper = st.selectbox(
                "Choose a previous year paper:",
                paper_options,
                index=0 if st.session_state.current_paper is None else 
                      next((i for i, p in enumerate(paper_options) 
                           if p == os.path.basename(st.session_state.paper_name)), 0)
            )
            
            selected_path = os.path.join(papers_dir, selected_paper)
            
            if st.button("🚀 Start/Load Paper", use_container_width=True):
                # Parse the PDF
                with st.spinner("Loading paper..."):
                    parser = QuestionParser(selected_path)
                    questions = parser.parse_questions()
                    answer_key = parser.extract_answer_key()
                    
                    if questions:
                        st.session_state.current_paper = selected_path
                        st.session_state.questions = questions
                        st.session_state.paper_name = selected_paper
                        st.session_state.answer_key = answer_key
                        st.session_state.answers = {}
                        st.session_state.current_question = 0
                        st.session_state.exam_submitted = False
                        st.rerun()
                    else:
                        st.error("Could not parse questions from this paper. Please try another one.")
        else:
            st.warning(f"No PDF files found in {papers_dir}")
            st.info("Please place JEE Mains PDF papers in the papers-2025 directory")
        
        st.markdown("---")
        
        # Show question navigation
        if st.session_state.questions:
            st.header("📋 Question Navigator")
            
            cols = st.columns(5)
            for idx, q in enumerate(st.session_state.questions):
                col_idx = idx % 5
                with cols[col_idx]:
                    is_answered = idx in st.session_state.answers
                    button_style = "answered" if is_answered else "not-answered"
                    
                    if st.button(
                        f"Q{q['number']}",
                        key=f"nav_{idx}",
                        use_container_width=True,
                        type="primary" if idx == st.session_state.current_question else "secondary"
                    ):
                        st.session_state.current_question = idx
                        st.rerun()
    
    # Main content area
    if st.session_state.questions:
        # Header
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.markdown(f"""
            <div class="exam-header">
                <h3 style="margin:0;">{st.session_state.paper_name}</h3>
                <p style="margin:5px 0 0 0; opacity: 0.9;">Total Questions: {len(st.session_state.questions)}</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            answered = len(st.session_state.answers)
            total = len(st.session_state.questions)
            st.metric("Answered", f"{answered}/{total}")
        
        with col3:
            if st.button("📤 Submit Exam", type="primary", use_container_width=True):
                st.session_state.exam_submitted = True
                st.rerun()
        
        st.markdown("---")
        
        if not st.session_state.exam_submitted:
            # Display current question
            current_idx = st.session_state.current_question
            question = st.session_state.questions[current_idx]
            
            # Subject badge
            subject_colors = {
                "Mathematics": "🔵",
                "Physics": "🟣",
                "Chemistry": "🟢",
                "General": "⚪"
            }
            subject_emoji = subject_colors.get(question['subject'], "⚪")
            st.caption(f"{subject_emoji} {question['subject']} - Question {question['number']}")
            
            # Question text
            st.markdown(f"""
            <div class="question-box">
                <div class="question-text">{question['text']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Options as radio buttons
            if question['options']:
                options_dict = {f"Option {i+1}": opt for i, opt in enumerate(question['options']) if opt}
                
                current_answer = st.session_state.answers.get(current_idx)
                
                selected = st.radio(
                    "Select your answer:",
                    options=options_dict.keys(),
                    format_func=lambda x: options_dict[x],
                    index=None if current_answer is None else current_answer,
                    key=f"q_{current_idx}",
                    label_visibility="collapsed"
                )
                
                if selected is not None:
                    selected_idx = list(options_dict.keys()).index(selected)
                    st.session_state.answers[current_idx] = selected_idx
                
                # Navigation buttons
                col1, col2, col3 = st.columns([1, 3, 1])
                with col1:
                    if current_idx > 0:
                        if st.button("⬅️ Previous", use_container_width=True):
                            st.session_state.current_question -= 1
                            st.rerun()
                
                with col3:
                    if current_idx < len(st.session_state.questions) - 1:
                        if st.button("Next ➡️", use_container_width=True):
                            st.session_state.current_question += 1
                            st.rerun()
            else:
                st.warning("No options available for this question")
        
        else:
            # Show results
            st.markdown("""
            <div class="score-card">
                <div class="score-number">Calculating...</div>
                <div>Your Results</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Calculate score
            correct = 0
            wrong = 0
            unattempted = 0
            
            results = []
            for idx, question in enumerate(st.session_state.questions):
                user_answer = st.session_state.answers.get(idx)
                actual_q_num = question['number']
                correct_answer = st.session_state.answer_key.get(actual_q_num)
                
                if user_answer is None:
                    unattempted += 1
                    status = "unattempted"
                elif correct_answer is not None and (user_answer + 1) == correct_answer:
                    correct += 1
                    status = "correct"
                else:
                    wrong += 1
                    status = "wrong"
                
                results.append({
                    'question': question,
                    'user_answer': user_answer,
                    'correct_answer': correct_answer,
                    'status': status
                })
            
            # Calculate score (assuming +4 for correct, -1 for wrong)
            total_score = correct * 4 - wrong * 1
            max_score = len(st.session_state.questions) * 4
            
            # Display score card
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Correct", correct, delta=f"+{correct*4} marks")
            with col2:
                st.metric("Wrong", wrong, delta=f"-{wrong} marks", delta_color="inverse")
            with col3:
                st.metric("Unattempted", unattempted)
            
            st.markdown(f"""
            <div class="score-card">
                <div style="font-size: 24px;">Total Score</div>
                <div class="score-number">{total_score} / {max_score}</div>
                <div style="font-size: 18px; margin-top: 10px;">
                    Accuracy: {correct/(correct+wrong)*100:.1f}% (if excluding unattempted)
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Show detailed solutions
            st.markdown("### 📖 Detailed Solutions")
            
            filter_option = st.selectbox(
                "Filter by:",
                ["All Questions", "Correct Only", "Wrong Only", "Unattempted Only"]
            )
            
            for result in results:
                show = True
                if filter_option == "Correct Only" and result['status'] != 'correct':
                    show = False
                elif filter_option == "Wrong Only" and result['status'] != 'wrong':
                    show = False
                elif filter_option == "Unattempted Only" and result['status'] != 'unattempted':
                    show = False
                
                if show:
                    q = result['question']
                    status_class = "correct-answer" if result['status'] == 'correct' else \
                                  "wrong-answer" if result['status'] == 'wrong' else ""
                    
                    with st.expander(
                        f"{'✅' if result['status'] == 'correct' else '❌' if result['status'] == 'wrong' else '⭕'} "
                        f"Question {q['number']} ({q['subject']})",
                        expanded=(result['status'] == 'wrong')
                    ):
                        st.markdown(f"**Question:** {q['text']}")
                        
                        if q['options']:
                            st.write("**Options:**")
                            for i, opt in enumerate(q['options']):
                                marker = ""
                                if result['user_answer'] == i:
                                    marker = "← Your Answer"
                                    if result['status'] == 'wrong':
                                        marker += " ❌"
                                if result['correct_answer'] == i + 1:
                                    marker += " ✓ Correct Answer" if not marker else " | ✓ Correct Answer"
                                
                                st.write(f"{i+1}. {opt} {marker}")
                        
                        if result['status'] == 'unattempted':
                            if result['correct_answer']:
                                st.info(f"Correct answer was: Option {result['correct_answer']}")
    
    else:
        # Welcome screen
        st.markdown("""
        <div style="text-align: center; padding: 50px;">
            <h1>🎯 Welcome to JEE Mains Practice Platform</h1>
            <p style="font-size: 18px; color: #666;">
                Select a previous year paper from the sidebar to start practicing
            </p>
            <div style="margin-top: 30px;">
                <div style="display: inline-block; padding: 20px; margin: 10px; background: #f0f4ff; border-radius: 10px;">
                    <h3>📝 Exam Interface</h3>
                    <p>Real exam-like interface with question navigator</p>
                </div>
                <div style="display: inline-block; padding: 20px; margin: 10px; background: #f0fff4; border-radius: 10px;">
                    <h3>✅ Instant Feedback</h3>
                    <p>Get immediate results with detailed analysis</p>
                </div>
                <div style="display: inline-block; padding: 20px; margin: 10px; background: #fff4f0; border-radius: 10px;">
                    <h3>📊 Performance Tracking</h3>
                    <p>Track your accuracy and improvement over time</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.info("💡 **Tip:** Papers are loaded from the `/workspace/papers-2025` directory. Make sure your PDF files are placed there.")


if __name__ == "__main__":
    main()
