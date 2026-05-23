import sys
# Python 3.13+ പതിപ്പുകളിൽ pydub ക്രാഷ് ആകാതിരിക്കാൻ audioop റീഡയറക്ട് ചെയ്യുന്നു
try:
    import audioop
except ImportError:
    import audioop_lts
    sys.modules['audioop'] = audioop_lts

import streamlit as st
import edge_tts
import asyncio
import io
import numpy as np
import pydub
from gtts import gTTS
from scipy.signal import butter, lfilter

# Streamlit Config & Custom Pro-Studio UI Theme
st.set_page_config(page_title="AI Voice Studio PRO", page_icon="🎙️", layout="wide")

# Custom Dark Studio CSS Styling
st.markdown("""
    <style>
    .main { background-color: #0f111a; color: #ffffff; }
    .stButton>button {
        background: linear-gradient(45deg, #ff4b4b, #ff7676);
        color: white; border: none; padding: 10px 25px;
        border-radius: 8px; font-weight: bold; width: 100%;
        transition: all 0.3s ease;
    }
    .stButton>button:hover { transform: scale(1.02); box-shadow: 0 4px 15px rgba(255,75,75,0.4); }
    h1, h2, h3 { color: #00ffcc !important; font-family: 'Poppins', sans-serif; }
    .stSlider>div>div>div>div { background-color: #00ffcc !important; }
    .css-10trblm { color: #ffffff; }
    </style>
    """, unsafe_allow_html=True)

st.title("🎙️ AI Multi-Language Voice Studio PRO")
st.markdown("<p style='color:#8a99ad; font-size:18px;'>പ്രൊഫഷണൽ ഓഡിയോ നിർമ്മാണവും എഡിറ്റിംഗും ഇനി ഒരിടത്ത്! (Malayalam, Arabic, English)</p>", unsafe_html=True)

# Sidebar for Navigation
option = st.sidebar.selectbox("🎛️ കൺട്രോൾ പാനൽ", ["🗣️ Text to Voice", "🎚️ Pro Audio Enhancer & Studio"])

# --- പൈത്തൺ ഫിൽട്ടർ ഫങ്ക്ഷനുകൾ (Bass & Treble EQ) ---
def butter_lowpass(cutoff, fs, order=5):
    return butter(order, cutoff, btype='low', fs=fs)

def butter_highpass(cutoff, fs, order=5):
    return butter(order, cutoff, btype='high', fs=fs)

def apply_eq(audio_segment, bass_gain, treble_gain):
    samples = np.array(audio_segment.get_array_of_samples(), dtype=np.float32)
    fs = audio_segment.frame_rate
    
    # Bass Booster
    if bass_gain != 0:
        b, a = butter_lowpass(250, fs, order=2)
        bass_layer = lfilter(b, a, samples)
        samples += bass_layer * (bass_gain / 10.0)
        
    # Treble Booster
    if treble_gain != 0:
        b, a = butter_highpass(4000, fs, order=2)
        treble_layer = lfilter(b, a, samples)
        samples += treble_layer * (treble_gain / 10.0)
        
    samples = np.clip(samples, -32768, 32767).astype(np.int16)
    return audio_segment._spawn(samples.tobytes())

# --- എക്കോ ഫങ്ക്ഷൻ ---
def apply_pure_echo(audio_segment, delay_ms, feedback, echo_count=3):
    if delay_ms == 0 or feedback == 0:
        return audio_segment
    output = audio_segment
    for i in range(1, echo_count + 1):
        attenuation = i * (12.0 * (1.0 - feedback + 0.1))
        echo_layer = audio_segment.minus_dB(attenuation)
        output = output.overlay(echo_layer, position=i * delay_ms)
    return output

# --- റീവെർബ് ഫങ്ക്ഷൻ (പ്രത്യേകം രൂപകൽപ്പന ചെയ്തത്) ---
def apply_studio_reverb(audio_segment, room_size):
    if room_size == 0:
        return audio_segment
    
    # റീവെർബ് ഇഫക്റ്റ് ലഭിക്കാൻ വളരെ ചെറിയ സമയ വ്യത്യാസങ്ങളിൽ നിരവധി ലെയറുകൾ മിക്സ് ചെയ്യുന്നു
    reverb_output = audio_segment
    delays = [20, 40, 65, 85] # മില്ലിസെക്കൻഡുകൾ
    
    for d in delays:
        # റൂം സൈസ് കൂടുന്നതിനനുസരിച്ച് റിവെർബിന്റെ ആഴം കൂടുന്നു
        gain_reduction = 15.0 - (room_size * 10.0)
        rev_layer = audio_segment.minus_dB(gain_reduction)
        reverb_output = reverb_output.overlay(rev_layer, position=d)
        
    return reverb_output

# ---------------------------------------------------------
# ഭാഗം 1: Text to Voice (Google TTS & Edge TTS)
# ---------------------------------------------------------
if option == "🗣️ Text to Voice":
    st.subheader("🗣️ Text to Natural Voice Converter")
    
    text = st.text_area("ടെക്സ്റ്റ് ഇവിടെ നൽകുക:", height=150, placeholder="നമസ്കാരം, സുഖമാണോ? നിങ്ങളുടെ ടെക്സ്റ്റ് ഇവിടെ ടൈപ്പ് ചെയ്യാം...")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        engine = st.selectbox("TTS Engine തിരഞ്ഞെടുക്കുക", ["Microsoft Edge TTS (Midhun/Sobhana)", "Google TTS"])
        
    with col2:
        if engine == "Microsoft Edge TTS (Midhun/Sobhana)":
            voice_options = {
                "Malayalam: Female (Sobhana)": "ml-IN-SobhanaNeural",
                "Malayalam: Male (Midhun)": "ml-IN-MidhunNeural",
                "Arabic: Female (Zariyah)": "ar-SA-ZariyahNeural",
                "Arabic: Male (Hamed)": "ar-SA-HamedNeural",
                "English: Female (Ava)": "en-US-AvaNeural",
                "English: Male (Andrew)": "en-US-AndrewNeural"
            }
        else:
            voice_options = {
                "Malayalam (Google Voice)": "ml",
                "Arabic (Google Voice)": "ar",
                "English (Google Voice)": "en"
            }
        selected_voice = st.selectbox("Voice തിരഞ്ഞെടുക്കുക", list(voice_options.keys()))
    
    with col3:
        speed = st.slider("വേഗത (Speed)", 0.5, 2.0, 1.0, 0.1)

    async def generate_edge_voice(text, voice_code, rate):
        communicate = edge_tts.Communicate(text, voice_code, rate=f"{int((rate - 1) * 100):+d}%")
        data = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                data += chunk["data"]
        return data

    if st.button("🔊 Voice ജനറേറ്റ് ചെയ്യുക", type="primary"):
        if text.strip():
            with st.spinner("സ്റ്റുഡിയോ ക്വാളിറ്റി ശബ്ദം ഉണ്ടാക്കുന്നു..."):
                try:
                    voice_code = voice_options[selected_voice]
                    
                    if "Microsoft Edge TTS" in engine:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        audio_bytes = loop.run_until_complete(generate_edge_voice(text, voice_code, speed))
                    else:
                        tts = gTTS(text=text, lang=voice_code)
                        fp = io.BytesIO()
                        tts.write_to_fp(fp)
                        audio_bytes = fp.getvalue()
                        
                        if speed != 1.0:
                            audio_segment = pydub.AudioSegment.from_file(io.BytesIO(audio_bytes), format="mp3")
                            new_sample_rate = int(audio_segment.frame_rate * speed)
                            audio_segment = audio_segment._spawn(audio_segment.raw_data, overrides={'frame_rate': new_sample_rate})
                            audio_segment = audio_segment.set_frame_rate(audio_segment.frame_rate)
                            out_io = io.BytesIO()
                            audio_segment.export(out_io, format="mp3")
                            audio_bytes = out_io.getvalue()
                    
                    st.success("✅ വോയ്‌സ് റെഡിയായിരിക്കുന്നു!")
                    st.audio(audio_bytes, format="audio/mp3")
                    st.download_button("📥 Download MP3", audio_bytes, file_name="ai_voice_pro.mp3", mime="audio/mp3")
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.warning("ദയവായി ടെക്സ്റ്റ് ടൈപ്പ് ചെയ്യുക!")

# ---------------------------------------------------------
# ഭാഗം 2: Pro Audio Enhancer & Studio (All Tools Included)
# ---------------------------------------------------------
elif option == "🎚️ Pro Audio Enhancer & Studio":
    st.subheader("🎚️ Pro Mastering Studio (All Professional Tools)")
    
    uploaded_file = st.file_uploader("ഓഡിയോ ഫയൽ അപ്‌ലോഡ് ചെയ്യുക (WAV, MP3)", type=["wav", "mp3"])

    if uploaded_file is not None:
        try:
            file_bytes = uploaded_file.read()
            audio_segment = pydub.AudioSegment.from_file(io.BytesIO(file_bytes))
            
            st.divider()
            c1, c2, c3 = st.columns(3)
            
            with c1:
                st.markdown("### 🔊 Master & Volume")
                vol_change = st.slider("Volume Booster (dB)", -20.0, 20.0, 3.5, 0.5)
                compressor_on = st.checkbox("⚡ Auto Compressor (Normalize)", value=True)
                
            with c2:
                st.markdown("### 🎸 Equalizer (EQ)")
                bass_boost = st.slider("Bass Booster 🔥", -10.0, 30.0, 5.0, 0.5)
                treble_boost = st.slider("Treble Booster ✨", -10.0, 30.0, 2.0, 0.5)

            with c3:
                st.markdown("### 🏛️ Professional Effects")
                # 1. റീവെർബ് നോബ് (പ്രത്യേകമായി ചേർത്തത്)
                reverb_level = st.slider("Studio Reverb (Room Size)", 0.0, 1.0, 0.3, 0.05)
                # 2. എക്കോ നോബ്
                echo_delay = st.slider("Echo Delay (Time ms)", 0, 1000, 0, 20)
                echo_feedback = st.slider("Echo Repeat (Feedback)", 0.0, 1.0, 0.4, 0.05)

            if st.button("🎛️ Apply Studio Effects", type="primary"):
                with st.spinner("ഓഡിയോ മാസ്റ്ററിംഗ് ചെയ്തുകൊണ്ടിരിക്കുന്നു..."):
                    
                    # 1. Volume മാറ്റുന്നു
                    processed = audio_segment + vol_change
                    
                    # 2. Advanced Equalizer (Bass & Treble)
                    processed = apply_eq(processed, bass_boost, treble_boost)
                    
                    # 3. Studio Reverb Effect (പ്രത്യേകമായി വർക്ക് ചെയ്യുന്നു)
                    if reverb_level > 0:
                        processed = apply_studio_reverb(processed, reverb_level)
                    
                    # 4. Pure Digital Echo Effect
                    if echo_delay > 0 and echo_feedback > 0:
                        processed = apply_pure_echo(processed, echo_delay, echo_feedback, echo_count=3)
                    
                    # 5. Pro Compressor / Normalizer
                    if compressor_on:
                        processed = pydub.effects.normalize(processed)
                    
                    # ഫയൽ എക്സ്പോർട്ട് ചെയ്യുന്നു
                    out_io = io.BytesIO()
                    processed.export(out_io, format="wav")
                    
                    st.success("🎯 മാസ്റ്ററിംഗ് പൂർത്തിയായി! നിങ്ങളുടെ പ്രൊഫഷണൽ ഫയൽ റെഡി.")
                    st.audio(out_io.getvalue(), format="audio/wav")
                    st.download_button("📥 Download Mastered File", out_io.getvalue(), "studio_mastered.wav", "audio/wav")
        except Exception as e:
            st.error(f"Error: {e}. ശരിയായ ഫയൽ അപ്‌ലോഡ് ചെയ്ത് വീണ്ടും ശ്രമിക്കുക.")

st.divider()
st.caption("Developed for Ashraf MJ • Powered by Advanced Scipy Filters, Google TTS, Edge-TTS & Pydub")
