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
# Custom CSS for exam-like interface with subject-specific colors
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
    /* Subject-specific colors */
    .subject-mathematics {
        border-left-color: #FF6B6B !important;
        background-color: #FFF5F5 !important;
    }
    .subject-physics {
        border-left-color: #4ECDC4 !important;
        background-color: #F0FFFE !important;
    }
    .subject-chemistry {
        border-left-color: #45B7D1 !important;
        background-color: #F0F9FF !important;
    }
    .subject-general {
        border-left-color: #96CEB4 !important;
        background-color: #F5FFF9 !important;
    }
</style>
""", unsafe_allow_html=True)

# Subject configuration with colors and emojis
SUBJECT_CONFIG = {
    "Mathematics": {"color": "#FF6B6B", "emoji": "📐", "bg": "#FFF5F5"},
    "Physics": {"color": "#4ECDC4", "emoji": "⚡", "bg": "#F0FFFE"},
    "Chemistry": {"color": "#45B7D1", "emoji": "🧪", "bg": "#F0F9FF"},
    "General": {"color": "#96CEB4", "emoji": "📚", "bg": "#F5FFF9"}
}


class QuestionParser:
    """Parse JEE Mains PDF papers and extract questions with options"""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.doc = pymupdf.open(pdf_path)
        
    def detect_subject(self, text: str) -> str:
        """Detect subject from question text"""
        text_lower = text.lower()
        
        # Physics keywords
        physics_keywords = ['physics', 'velocity', 'acceleration', 'force', 'energy', 
                          'momentum', 'electric', 'magnetic', 'field', 'current', 
                          'voltage', 'resistance', 'capacitor', 'inductor', 'wave',
                          'optics', 'lens', 'mirror', 'thermodynamics', 'entropy',
                          'photon', 'electron', 'proton', 'neutron', 'atom', 'nuclear']
        
        # Chemistry keywords
        chemistry_keywords = ['chemistry', 'reaction', 'compound', 'molecule', 'ion',
                            'acid', 'base', 'salt', 'oxidation', 'reduction', 'bond',
                            'organic', 'inorganic', 'polymer', 'catalyst', 'equilibrium',
                            'solution', 'concentration', 'mole', 'atomic', 'periodic',
                            'hydrocarbon', 'alcohol', 'ketone', 'aldehyde']
        
        # Mathematics keywords
        math_keywords = ['mathematics', 'maths', 'matrix', 'determinant', 'vector',
                        'integral', 'derivative', 'differential', 'equation', 'function',
                        'trigonometry', 'geometry', 'algebra', 'calculus', 'probability',
                        'statistics', 'coordinate', 'circle', 'parabola', 'ellipse',
                        'hyperbola', 'limit', 'continuity', 'series', 'sequence']
        
        physics_count = sum(1 for kw in physics_keywords if kw in text_lower)
        chemistry_count = sum(1 for kw in chemistry_keywords if kw in text_lower)
        math_count = sum(1 for kw in math_keywords if kw in text_lower)
        
        max_count = max(physics_count, chemistry_count, math_count)
        
        if max_count == 0:
            return "General"
        elif physics_count == max_count:
            return "Physics"
        elif chemistry_count == max_count:
            return "Chemistry"
        else:
            return "Mathematics"
    
    def extract_questions(self) -> List[Dict]:
        """Extract questions from PDF using improved parsing for JEE format"""
        # Get full text from all pages
        full_text = ""
        for page in self.doc:
            full_text += page.get_text() + "\n"
        
        questions = []
        
        # Pattern to match questions: Q followed by number and dot
        # Split by question pattern
        question_splits = re.split(r'(Q\d+\.)', full_text)
        
        # Process splits - they alternate between delimiter and content
        i = 1
        while i < len(question_splits) - 1:
            q_marker = question_splits[i]  # e.g., "Q1."
            content = question_splits[i + 1]
            
            # Extract question number
            q_num_match = re.match(r'Q(\d+)\.', q_marker)
            if not q_num_match:
                i += 2
                continue
            
            q_num = int(q_num_match.group(1))
            
            # Split content into lines
            lines = content.strip().split('\n')
            
            # Find where options start (look for (1), (2), (3), (4) pattern)
            q_text_lines = []
            opt_lines = []
            in_options = False
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Check if this line starts options section
                if re.match(r'^\(1\)', line):
                    in_options = True
                    opt_lines.append(line)
                elif in_options:
                    opt_lines.append(line)
                else:
                    q_text_lines.append(line)
            
            # Join question text
            q_text = ' '.join(q_text_lines).strip()
            
            # Extract options - handle both inline and separate line formats
            options = []
            opt_text_combined = ' '.join(opt_lines)
            
            # Try to extract options with text: (1) text (2) text ...
            opt_matches = re.findall(r'\(([1-4])\)\s*([^\(]*?)(?=\([1-4]\)|$)', opt_text_combined)
            
            if opt_matches and len(opt_matches) >= 1:
                # We found options with text
                for opt_num_str, opt_text in opt_matches:
                    opt_num = int(opt_num_str)
                    opt_text = opt_text.strip()
                    # Pad options array if needed
                    while len(options) < opt_num - 1:
                        options.append('')
                    if opt_num > len(options):
                        options.append(opt_text)
                    else:
                        options[opt_num - 1] = opt_text
            else:
                # Options might be just labels without extractable text (images/formulas)
                # Check if we have (1), (2), (3), (4) markers
                if re.search(r'\([1-4]\)', opt_text_combined):
                    # Found option markers but no text - likely image-based options
                    options = ['Option 1', 'Option 2', 'Option 3', 'Option 4']
                else:
                    # No options found at all
                    options = ['Option 1', 'Option 2', 'Option 3', 'Option 4']
            
            # Ensure we have exactly 4 options
            valid_opts = [o for o in options if o and len(o.strip()) > 0]
            if len(valid_opts) < 4:
                while len(valid_opts) < 4:
                    valid_opts.append(f'Option {len(valid_opts)+1}')
            
            if q_text:  # Only add if we have question text
                questions.append({
                    'number': q_num,
                    'text': q_text,
                    'options': valid_opts[:4],
                    'subject': self.detect_subject(q_text)
                })
            
            i += 2
        
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
            
            # Subject badge with color coding
            subject_config = SUBJECT_CONFIG.get(question['subject'], SUBJECT_CONFIG["General"])
            subject_emoji = subject_config["emoji"]
            subject_color = subject_config["color"]
            subject_class = f"subject-{question['subject'].lower()}"
            
            st.markdown(f"""
            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                <span style="font-size: 20px; margin-right: 8px;">{subject_emoji}</span>
                <span style="background-color: {subject_color}; color: white; padding: 4px 12px; border-radius: 15px; font-weight: bold; font-size: 14px;">
                    {question['subject']}
                </span>
                <span style="margin-left: 10px; color: #666;">Question {question['number']}</span>
            </div>
            """, unsafe_allow_html=True)
            
            # Question text with subject-specific border color
            st.markdown(f"""
            <div class="question-box {subject_class}">
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
