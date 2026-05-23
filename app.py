import streamlit as st
import edge_tts
import asyncio
import io
import numpy as np
from pedalboard import Pedalboard, Reverb, Compressor, Delay, Gain, LowShelfFilter, HighShelfFilter
from pedalboard.io import AudioFile

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
        async len_chunk = 0
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
# ഭാഗം 2: Audio Enhancer & Editor (Bass, Treble, Volume)
# ---------------------------------------------------------
elif option == "Audio Enhancer & Editor":
    st.subheader("🎚️ Audio Enhancer & Volume Booster")
    
    uploaded_file = st.file_uploader("ഓഡിയോ ഫയൽ അപ്‌ലോഡ് ചെയ്യുക (wav, mp3)", type=["wav", "mp3"])

    if uploaded_file is not None:
        try:
            # Pedalboard AudioFile ഉപയോഗിച്ച് ഫയൽ റീഡ് ചെയ്യുന്നു
            with AudioFile(io.BytesIO(uploaded_file.read())) as f:
                audio_data = f.read(f.frames)
                sample_rate = f.samplerate
            
            st.divider()
            c1, c2, c3 = st.columns(3)
            
            with c1:
                st.markdown("### 🔊 Basic")
                vol = st.slider("Volume (dB)", -10.0, 30.0, 3.5)
                comp_thresh = st.slider("Compression (Threshold)", -40, 0, -20)
                
            with c2:
                st.markdown("### 🎸 EQ (Bass & Treble)")
                bass = st.slider("Bass Boost", -10.0, 20.0, 0.0)
                treble = st.slider("Treble Boost", -10.0, 20.0, 0.0)

            with c3:
                st.markdown("### 🏛️ Effects")
                rev_wet = st.slider("Reverb (Wet Level)", 0.0, 1.0, 0.1)
                del_mix = st.slider("Delay / Echo", 0.0, 1.0, 0.0)

            if st.button("Apply Effects", type="primary"):
                with st.spinner("പ്രോസസ്സ് ചെയ്യുന്നു..."):
                    # Pedalboard Pipeline
                    board = Pedalboard([
                        LowShelfFilter(cutoff_frequency_hz=250, gain_db=bass),
                        HighShelfFilter(cutoff_frequency_hz=4000, gain_db=treble),
                        Gain(gain_db=vol),
                        Compressor(threshold_db=comp_thresh, ratio=4),
                        Reverb(room_size=0.6, wet_level=rev_wet),
                        Delay(delay_seconds=0.4, feedback=0.3, mix=del_mix)
                    ])

                    processed_audio = board(audio_data, sample_rate)
                    
                    # Normalization (ശബ്ദം വികൃതമാകാതിരിക്കാൻ)
                    peak = np.max(np.abs(processed_audio))
                    if peak > 0:
                        processed_audio = processed_audio / peak

                    # സേവ് ചെയ്യുന്നു
                    out_io = io.BytesIO()
                    with AudioFile(out_io, 'w', sample_rate, processed_audio.shape[0]) as f:
                        f.write(processed_audio)
                    
                    st.success("✅ റെഡി!")
                    st.audio(out_io.getvalue())
                    st.download_button("📥 Download Enhanced File", out_io.getvalue(), "enhanced.wav", "audio/wav")
        except Exception as e:
            st.error(f"Error: {e}")

st.divider()
st.caption("Developed for Ashraf MJ • Powered by Edge-TTS & Pedalboard")