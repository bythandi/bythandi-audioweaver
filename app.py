import os
import re
import tempfile
from io import BytesIO

import streamlit as st
import pdfplumber
from gtts import gTTS
from pydub import AudioSegment


# ========== PAGE CONFIG ==========

st.set_page_config(
    page_title="ByThandi AudioWeaver",
    page_icon="🌸",
    layout="centered",
)


# ========== BYTHANDI BRAND STYLING ==========

st.markdown("""
<style>
    /* Main container */
    .stApp {
        background: linear-gradient(135deg, #fff1ea 0%, #e6f0fc 100%);
    }
    
    /* Header styling */
    .bythandi-header {
        text-align: center;
        color: #152d69;
        font-size: 2.5rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
        letter-spacing: -0.5px;
    }
    
    .bythandi-subtitle {
        text-align: center;
        color: #521305;
        font-size: 1.1rem;
        margin-bottom: 2rem;
        opacity: 0.8;
    }
    
    /* Button styling */
    .stButton > button {
        background-color: #f7931e !important;
        color: white !important;
        font-weight: 600 !important;
        border: none !important;
        padding: 0.75rem 2rem !important;
        border-radius: 8px !important;
        width: 100%;
        transition: all 0.3s ease !important;
    }
    
    .stButton > button:hover {
        background-color: #e8850a !important;
        box-shadow: 0 4px 12px rgba(247, 147, 30, 0.3) !important;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: #e6f0fc;
        color: #152d69;
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #152d69 !important;
        color: white !important;
    }
    
    /* Success/info boxes */
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    /* Footer */
    .bythandi-footer {
        text-align: center;
        color: #521305;
        font-size: 0.9rem;
        margin-top: 3rem;
        padding-top: 1rem;
        border-top: 1px solid #ffcb8f;
    }
</style>
""", unsafe_allow_html=True)


# ========== TEXT PROCESSING ==========

def clean_text(text: str) -> str:
    """Clean and normalize text for TTS."""
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove weird characters but keep punctuation
    text = re.sub(r'[^\w\s.,!?;:\'\"-]', ' ', text)
    
    # Clean up multiple spaces
    text = re.sub(r' +', ' ', text)
    
    return text.strip()


def extract_pdf_text(file_content: bytes) -> tuple[str, int]:
    """Extract text from PDF file content. Returns (text, page_count)."""
    all_text = []
    
    with pdfplumber.open(BytesIO(file_content)) as pdf:
        page_count = len(pdf.pages)
        
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                all_text.append(page_text)
    
    combined = "\n".join(all_text)
    cleaned = clean_text(combined)
    
    return cleaned, page_count


# ========== TEXT TO SPEECH ==========

def text_to_speech(
    text: str,
    language: str = "en",
    slow: bool = False,
    output_format: str = "mp3",
    progress_callback=None,
) -> bytes:
    """Convert text to speech using gTTS. Returns audio bytes."""
    
    # Split text into chunks (gTTS has limits)
    max_chunk = 5000
    chunks = [text[i:i+max_chunk] for i in range(0, len(text), max_chunk)]
    total_chunks = len(chunks)
    
    # Generate audio for each chunk
    audio_segments = []
    
    for i, chunk in enumerate(chunks, 1):
        if progress_callback:
            progress_callback(i / total_chunks, f"Processing chunk {i}/{total_chunks}...")
        
        # Generate speech
        tts = gTTS(text=chunk, lang=language, slow=slow)
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tts.save(tmp.name)
            segment = AudioSegment.from_mp3(tmp.name)
            audio_segments.append(segment)
            os.unlink(tmp.name)
    
    # Combine all segments
    if progress_callback:
        progress_callback(0.95, "Combining audio...")
    
    combined = audio_segments[0]
    for segment in audio_segments[1:]:
        combined += segment
    
    # Export to bytes
    output_buffer = BytesIO()
    combined.export(output_buffer, format=output_format)
    output_buffer.seek(0)
    
    if progress_callback:
        progress_callback(1.0, "Complete!")
    
    return output_buffer.getvalue()


# ========== MAIN APP ==========

# Header
st.markdown('<div class="bythandi-header">🌸 ByThandi AudioWeaver</div>', unsafe_allow_html=True)
st.markdown('<div class="bythandi-subtitle">Converting text to accessible audio</div>', unsafe_allow_html=True)

# Input tabs
tab_pdf, tab_text = st.tabs(["📄 PDF Upload", "✍️ Text Input"])

text_content = None
file_name = "audio"

with tab_pdf:
    st.write("Upload a PDF document to convert to audio:")
    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=["pdf"],
        label_visibility="collapsed",
    )
    
    if uploaded_file:
        with st.spinner("Reading PDF..."):
            try:
                text_content, page_count = extract_pdf_text(uploaded_file.getvalue())
                file_name = os.path.splitext(uploaded_file.name)[0]
                st.success(f"✅ Extracted {len(text_content):,} characters from {page_count} page(s)")
            except Exception as e:
                st.error(f"❌ Error reading PDF: {e}")
                text_content = None

with tab_text:
    st.write("Enter text to convert to audio:")
    text_input = st.text_area(
        "Text input",
        height=200,
        placeholder="Paste or type your text here...",
        label_visibility="collapsed",
    )
    
    if text_input and text_input.strip():
        text_content = clean_text(text_input)
        file_name = "text_audio"

# Settings
st.markdown("---")
col1, col2, col3 = st.columns(3)

with col1:
    language = st.selectbox(
        "Language",
        options=["en", "pt", "ja", "fr", "es"],
        format_func=lambda x: {
            "en": "🇬🇧 English",
            "pt": "🇵🇹 Portuguese", 
            "ja": "🇯🇵 Japanese",
            "fr": "🇫🇷 French",
            "es": "🇪🇸 Spanish",
        }[x],
    )

with col2:
    speed = st.selectbox(
        "Speed",
        options=["Normal", "Slow"],
    )

with col3:
    output_format = st.selectbox(
        "Format",
        options=["mp3", "wav"],
    )

# Generate button
st.markdown("---")

if st.button("🎧 Generate Audio", use_container_width=True):
    if not text_content or len(text_content) < 10:
        st.error("❌ Please provide some text to convert (either upload a PDF or enter text).")
    else:
        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        def update_progress(value, message):
            progress_bar.progress(value)
            status_text.text(message)
        
        try:
            with st.spinner("Generating audio..."):
                audio_bytes = text_to_speech(
                    text=text_content,
                    language=language,
                    slow=(speed == "Slow"),
                    output_format=output_format,
                    progress_callback=update_progress,
                )
            
            # Clear progress
            progress_bar.empty()
            status_text.empty()
            
            # Success!
            st.success("🎉 Your audio is ready!")
            
            # Audio player
            st.audio(audio_bytes, format=f"audio/{output_format}")
            
            # Download button
            st.download_button(
                label=f"⬇️ Download {output_format.upper()}",
                data=audio_bytes,
                file_name=f"{file_name}.{output_format}",
                mime=f"audio/{output_format}",
                use_container_width=True,
            )
            
        except Exception as e:
            progress_bar.empty()
            status_text.empty()
            st.error(f"❌ Error generating audio: {e}")

# Footer
st.markdown("---")
st.markdown(
    '<div class="bythandi-footer">Made with 💛 by ByThandi • Accessibility through audio</div>',
    unsafe_allow_html=True,
)
