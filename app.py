import streamlit as st
import edge_tts
import asyncio
import io
import numpy as np
from scipy.io import wavfile
import pydub

# Streamlit Config
st.set_page_config(page_title="AI Voice Studio", page_icon="🎙️", layout="wide")

st.title("🎙️ AI Multi-Language Voice Studio")
st.markdown("ഓഡിയോ നിർമ്മാണവും എഡിറ്റിംഗും ഇനി ഒരിടത്ത്! (Malayalam, Arabic, English)")

# Sidebar for Navigation
option = st.sidebar.selectbox("എന്ത് ചെയ്യണം?", ["Text to Voice", "Audio Enhancer & Editor"])

# ---------------------------------------------------------
# ഭാഗം 1: Text to Voice (മലയാളം, അറബിക്, ഇംഗ്ലീഷ്)
# ---------------------------------------------------------
if option == "Text to Voice":
    st.subheader("🗣️ Text to Natural Voice Converter")
    
    text = st.text_area("ടെക്സ്റ്റ് ഇവിടെ നൽകുക:", height=150, placeholder="നമസ്കാരം, സുഖമാണോ?")
    
    col1, col2 = st.columns(2)
    with col1:
        voice_options = {
            "Malayalam: Female (Sobhana)": "ml-IN-SobhanaNeural",
            "Malayalam: Male (Midhun)": "ml-IN-MidhunNeural",
            "Arabic: Female (Zariyah - Saudi)": "ar-SA-ZariyahNeural",
            "Arabic: Male (Hamed - Saudi)": "ar-SA-HamedNeural",
            "English: Female (Ava)": "en-US-AvaNeural",
            "English: Male (Andrew)": "en-US-AndrewNeural"
        }
        selected_voice = st.selectbox("Voice തിരഞ്ഞെടുക്കുക", list(voice_options.keys()))
    
    with col2:
        speed = st.slider("വേഗത (Speed)", 0.5, 2.0, 1.0, 0.1)

    async def generate_voice(text, voice, rate):
        communicate = edge_tts.Communicate(text, voice_options[voice], rate=f"{int((rate - 1) * 100):+d}%")
        data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                data += chunk["data"]
        return data

    if st.button("🔊 Voice ആക്കുക", type="primary"):
        if text.strip():
            with st.spinner("ശബ്ദം ഉണ്ടാക്കുന്നു..."):
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    audio_bytes = loop.run_until_complete(generate_voice(text, selected_voice, speed))
                    
                    st.audio(audio_bytes, format="audio/mp3")
                    st.download_button("📥 Download MP3", audio_bytes, file_name="ai_voice.mp3", mime="audio/mp3")
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.warning("ദയവായി ടെക്സ്റ്റ് ടൈപ്പ് ചെയ്യുക!")

# ---------------------------------------------------------
# ഭാഗം 2: Audio Enhancer & Editor (Volume & Pitch)
# ---------------------------------------------------------
elif option == "Audio Enhancer & Editor":
    st.subheader("🎚️ Audio Enhancer & Volume Booster")
    
    uploaded_file = st.file_uploader("ഓഡിയോ ഫയൽ അപ്‌ലോഡ് ചെയ്യുക (wav, mp3)", type=["wav", "mp3"])

    if uploaded_file is not None:
        try:
            # pydub ഉപയോഗിച്ച് ഓഡിയോ ലോഡ് ചെയ്യുന്നു (MP3/WAV സപ്പോർട്ട് ചെയ്യാൻ)
            file_bytes = uploaded_file.read()
            audio_segment = pydub.AudioSegment.from_file(io.BytesIO(file_bytes))
            
            st.divider()
            c1, c2 = st.columns(2)
            
            with c1:
                st.markdown("### 🔊 Basic Settings")
                vol_change = st.slider("Volume Booster (dB)", -20.0, 20.0, 3.5, 0.5)
                
            with c2:
                st.markdown("### 🎼 Pitch Settings")
                pitch_change = st.slider("Change Pitch / Speed", 0.5, 2.0, 1.0, 0.1)

            if st.button("Apply Effects", type="primary"):
                with st.spinner("പ്രോസസ്സ് ചെയ്യുന്നു..."):
                    # 1. Volume മാറ്റുന്നു
                    processed = audio_segment + vol_change
                    
                    # 2. Pitch/Speed മാറ്റുന്നു
                    if pitch_change != 1.0:
                        new_sample_rate = int(processed.frame_rate * pitch_change)
                        processed = processed._spawn(processed.raw_data, overrides={'frame_rate': new_sample_rate})
                        processed = processed.set_frame_rate(audio_segment.frame_rate)
                    
                    # എക്സ്പോർട്ട് ചെയ്യുന്നു
                    out_io = io.BytesIO()
                    processed.export(out_io, format="wav")
                    
                    st.success("✅ റെഡി!")
                    st.audio(out_io.getvalue(), format="audio/wav")
                    st.download_button("📥 Download Enhanced File", out_io.getvalue(), "enhanced.wav", "audio/wav")
        except Exception as e:
            st.error(f"Error: {e}. Please try uploading a proper WAV or MP3 file.")

st.divider()
st.caption("Developed for Ashraf MJ • Powered by Edge-TTS & Scipy/Pydub")
