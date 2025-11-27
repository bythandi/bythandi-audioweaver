import os
import re
import tempfile
import subprocess
from io import BytesIO

import streamlit as st
import pdfplumber
from gtts import gTTS
from deep_translator import GoogleTranslator


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
    
    /* Logo container */
    .logo-container {
        display: flex;
        justify-content: center;
        margin-bottom: 1rem;
    }
    
    /* Header styling */
    .bythandi-header {
        text-align: center;
        font-size: 2.5rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
        letter-spacing: -0.5px;
        background: linear-gradient(135deg, #152d69 0%, #f7931e 50%, #521305 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
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


# ========== LANGUAGE CONFIG ==========

LANGUAGES = {
    "en": "🇬🇧 English",
    "pt": "🇵🇹 Portuguese",
    "ja": "🇯🇵 Japanese",
    "fr": "🇫🇷 French",
    "es": "🇪🇸 Spanish",
}


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


# ========== TRANSLATION ==========

def translate_text(text: str, source_lang: str, target_lang: str, progress_callback=None) -> str:
    """Translate text from source language to target language."""
    if source_lang == target_lang:
        return text
    
    if not text or len(text.strip()) == 0:
        raise ValueError("No text to translate")
    
    # deep-translator has a 5000 char limit per request, so chunk it
    max_chunk = 4500
    chunks = [text[i:i+max_chunk] for i in range(0, len(text), max_chunk)]
    total_chunks = len(chunks)
    
    translated_chunks = []
    
    for i, chunk in enumerate(chunks, 1):
        if progress_callback:
            progress_callback(0.1 + (0.2 * i / total_chunks), f"Translating chunk {i}/{total_chunks}...")
        
        translator = GoogleTranslator(source=source_lang, target=target_lang)
        translated = translator.translate(chunk)
        
        if translated:
            translated_chunks.append(translated)
    
    result = " ".join(translated_chunks)
    
    if not result or len(result.strip()) == 0:
        raise ValueError("Translation returned empty result")
    
    return result


# ========== TEXT TO SPEECH ==========

def text_to_speech(
    text: str,
    language: str = "en",
    slow: bool = False,
    output_format: str = "mp3",
    progress_callback=None,
    progress_offset: float = 0.3,
) -> bytes:
    """Convert text to speech using gTTS. Returns audio bytes."""
    
    if not text or len(text.strip()) == 0:
        raise ValueError("No text to convert to speech")
    
    # Split text into chunks (gTTS has limits)
    max_chunk = 5000
    chunks = [text[i:i+max_chunk] for i in range(0, len(text), max_chunk)]
    total_chunks = len(chunks)
    
    # Create temp directory for processing
    with tempfile.TemporaryDirectory() as temp_dir:
        chunk_files = []
        
        # Generate audio for each chunk
        for i, chunk in enumerate(chunks, 1):
            if progress_callback:
                progress = progress_offset + (0.5 * i / total_chunks)
                progress_callback(progress, f"Generating audio {i}/{total_chunks}...")
            
            # Generate speech
            tts = gTTS(text=chunk, lang=language, slow=slow)
            
            # Save chunk to temp file
            chunk_path = os.path.join(temp_dir, f"chunk_{i:03d}.mp3")
            tts.save(chunk_path)
            chunk_files.append(chunk_path)
        
        # Verify files were created
        for chunk_path in chunk_files:
            if not os.path.exists(chunk_path):
                raise ValueError(f"Audio chunk was not created: {chunk_path}")
            if os.path.getsize(chunk_path) == 0:
                raise ValueError(f"Audio chunk is empty: {chunk_path}")
        
        # Combine chunks
        if progress_callback:
            progress_callback(0.85, "Combining audio...")
        
        if len(chunk_files) == 1:
            # Single chunk - just read it
            combined_mp3 = chunk_files[0]
        else:
            # Multiple chunks - concatenate with ffmpeg
            combined_mp3 = os.path.join(temp_dir, "combined.mp3")
            list_file = os.path.join(temp_dir, "files.txt")
            
            # Create file list for ffmpeg
            with open(list_file, "w") as f:
                for chunk_path in chunk_files:
                    f.write(f"file '{chunk_path}'\n")
            
            # Concatenate using ffmpeg
            result = subprocess.run([
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", list_file, "-c", "copy", combined_mp3
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                raise ValueError(f"FFmpeg concat failed: {result.stderr}")
        
        # Convert format if needed
        if output_format == "wav":
            if progress_callback:
                progress_callback(0.95, "Converting to WAV...")
            
            output_path = os.path.join(temp_dir, "output.wav")
            result = subprocess.run([
                "ffmpeg", "-y", "-i", combined_mp3, output_path
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                raise ValueError(f"FFmpeg convert failed: {result.stderr}")
        else:
            output_path = combined_mp3
        
        # Verify final output
        if not os.path.exists(output_path):
            raise ValueError("Final audio file was not created")
        if os.path.getsize(output_path) == 0:
            raise ValueError("Final audio file is empty")
        
        # Read final audio bytes
        with open(output_path, "rb") as f:
            audio_bytes = f.read()
        
        if len(audio_bytes) == 0:
            raise ValueError("Audio bytes are empty")
        
        if progress_callback:
            progress_callback(1.0, "Complete!")
        
        return audio_bytes


# ========== MAIN APP ==========

# Logo (hosted on GitHub)
LOGO_URL = "https://raw.githubusercontent.com/bythandi/bythandi-audioweaver/main/bythandi%20logo.svg"

st.markdown(
    f'''
    <div style="display: flex; justify-content: center; margin-bottom: 1rem;">
        <img src="{LOGO_URL}" width="150">
    </div>
    ''',
    unsafe_allow_html=True
)

# Header
st.markdown('<div class="bythandi-header">AudioWeaver</div>', unsafe_allow_html=True)
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

# Language settings
col1, col2 = st.columns(2)

with col1:
    source_lang = st.selectbox(
        "Source Language",
        options=list(LANGUAGES.keys()),
        format_func=lambda x: LANGUAGES[x],
        help="The language of your original text",
    )

with col2:
    target_lang = st.selectbox(
        "Output Language",
        options=list(LANGUAGES.keys()),
        format_func=lambda x: LANGUAGES[x],
        help="The language for the audio output",
    )

# Show translation notice
if source_lang != target_lang:
    st.info(f"📝 Text will be translated from {LANGUAGES[source_lang]} to {LANGUAGES[target_lang]} before generating audio.")

# Other settings
col3, col4 = st.columns(2)

with col3:
    speed = st.selectbox(
        "Speed",
        options=["Normal", "Slow"],
    )

with col4:
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
            progress_bar.progress(min(value, 1.0))
            status_text.text(message)
        
        try:
            # Translation step (if needed)
            if source_lang != target_lang:
                update_progress(0.05, f"Translating to {LANGUAGES[target_lang]}...")
                text_to_speak = translate_text(text_content, source_lang, target_lang, update_progress)
            else:
                text_to_speak = text_content
                update_progress(0.3, "Preparing audio generation...")
            
            # Verify we have text to speak
            if not text_to_speak or len(text_to_speak.strip()) < 10:
                raise ValueError("Not enough text to generate audio after processing")
            
            # Generate audio
            audio_bytes = text_to_speech(
                text=text_to_speak,
                language=target_lang,
                slow=(speed == "Slow"),
                output_format=output_format,
                progress_callback=update_progress,
                progress_offset=0.3,
            )
            
            # Clear progress
            progress_bar.empty()
            status_text.empty()
            
            # Verify audio was generated
            if not audio_bytes or len(audio_bytes) == 0:
                raise ValueError("No audio was generated")
            
            # Success!
            st.success("🎉 Your audio is ready!")
            
            # Audio player
            st.audio(audio_bytes, format=f"audio/{output_format}")
            
            # Download button
            st.download_button(
                label=f"⬇️ Download {output_format.upper()}",
                data=audio_bytes,
                file_name=f"{file_name}_{target_lang}.{output_format}",
                mime=f"audio/{output_format}",
                use_container_width=True,
            )
            
        except Exception as e:
            progress_bar.empty()
            status_text.empty()
            st.error(f"❌ Error: {e}")

# Footer
st.markdown("---")
st.markdown(
    '<div class="bythandi-footer">Made with 💛 by ByThandi • Accessibility through audio</div>',
    unsafe_allow_html=True,
)
