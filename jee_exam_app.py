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
        
    def extract_questions(self) -> List[Dict]:
        """Extract questions from PDF using position-based parsing"""
        all_blocks = []
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
                        bbox = block.get('bbox', [])
                        y_pos = bbox[1] if len(bbox) > 1 else 0
                        x_pos = bbox[0] if len(bbox) > 0 else 0
                        all_blocks.append({
                            'page': page_num,
                            'y': y_pos,
                            'x': x_pos,
                            'text': full_text
                        })
        
        # Sort by page, then by y position (with tolerance), then by x
        all_blocks.sort(key=lambda b: (b['page'], int(b['y'] // 10) * 10, b['x']))
        
        questions = []
        current_q_num = None
        current_q_text = ''
        current_opts = []
        
        for block in all_blocks:
            text = block['text'].strip()
            
            # Check for question start: Q1., Q10., etc.
            q_match = re.match(r'^Q(\d+)\.?\s*(.*)$', text, re.IGNORECASE)
            
            if q_match:
                # Save previous question
                if current_q_num is not None:
                    valid_opts = [o for o in current_opts if o and len(o.strip()) > 0]
                    if len(valid_opts) < 2:
                        valid_opts = ['Numerical Answer']
                    questions.append({
                        'number': current_q_num,
                        'text': current_q_text.strip(),
                        'options': valid_opts
                    })
                
                current_q_num = int(q_match.group(1))
                current_q_text = q_match.group(2).strip()
                current_opts = []
            elif re.match(r'^\(([1-4])\)\s*(.*)$', text):
                # Option line like '(1) value (2) value' or just '(1)'
                opt_matches = re.findall(r'\(([1-4])\)\s*([^\(]+?)(?=\([1-4]\)|$)', text)
                for opt_num_str, opt_text in opt_matches:
                    opt_num = int(opt_num_str)
                    opt_text = opt_text.strip()
                    while len(current_opts) < opt_num:
                        current_opts.append('')
                    if opt_text:
                        current_opts[opt_num - 1] = opt_text
            elif current_q_num and not current_opts:
                # Continue question text
                current_q_text += ' ' + text
            elif current_q_num and current_opts and len(current_opts) > 0:
                # Continue last option
                current_opts[-1] += ' ' + text
        
        # Save last question
        if current_q_num is not None:
            valid_opts = [o for o in current_opts if o and len(o.strip()) > 0]
            if len(valid_opts) < 2:
                valid_opts = ['Numerical Answer']
            questions.append({
                'number': current_q_num,
                'text': current_q_text.strip(),
                'options': valid_opts
            })
        
        return questions
    
    def extract_answer_key(self) -> Dict[int, int]:
        """Extract answer key from PDF"""
        text = ''
        for page in self.doc:
            text += page.get_text()
        
        answer_key = {}
        
        # Look for patterns like "1. (1)" or "Q1. (1)" in answer key sections
        # First try to find answer key section
        answer_section = re.search(r'ANSWER\s*KEY.*?(?=SECTION|$)', text, re.IGNORECASE | re.DOTALL)
        search_text = answer_section.group(0) if answer_section else text
        
        # Extract question number and answer
        matches = re.findall(r'(\d+)\.\s*\((\d+)\)', search_text)
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
        
        # Default papers directory - using relative path
        papers_dir = "papers-2025"
        
        # Check if directory exists, if not use current directory
        if not os.path.exists(papers_dir):
            papers_dir = "."
        
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
                    questions = parser.extract_questions()
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
        st.info("💡 **Tip:** Papers are loaded from the `papers-2025` directory. Make sure your PDF files are placed there.")


if __name__ == "__main__":
    main()
