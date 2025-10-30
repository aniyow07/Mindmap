import streamlit as st
import os
import tempfile
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ==================== THEME SELECTOR ====================
if 'theme' not in st.session_state:
    st.session_state.theme = "Alive 2007"

# Theme toggle in sidebar
with st.sidebar:
    st.session_state.theme = st.radio(
        "🎵 SELECT THEME:",
        ("Alive 2007", "Discovery"),
        index=0 if st.session_state.theme == "Alive 2007" else 1
    )

# ==================== DYNAMIC STYLING ====================
st.set_page_config(page_title="AutoMap", layout="wide", initial_sidebar_state="expanded")

if st.session_state.theme == "Alive 2007":
    # ALIVE 2007 DARK THEME
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;600;700&family=Orbitron:wght@700;900&display=swap');
        
        /* Global Dark Theme - Alive 2007 */
        .stApp {
            background: #000000;
            background-image: 
                radial-gradient(ellipse at top, rgba(0, 60, 255, 0.15) 0%, transparent 50%),
                radial-gradient(ellipse at bottom, rgba(255, 0, 60, 0.15) 0%, transparent 50%);
            color: #ffffff;
            font-family: 'Rajdhani', sans-serif;
        }
        
        /* Hide Streamlit branding */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* Pyramid Background Effect */
        .stApp::before {
            content: "";
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 0;
            height: 0;
            border-left: 400px solid transparent;
            border-right: 400px solid transparent;
            border-bottom: 600px solid rgba(0, 60, 255, 0.03);
            pointer-events: none;
            z-index: 0;
            filter: blur(2px);
        }
        
        /* LED Grid Effect */
        .stApp::after {
            content: "";
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-image: 
                linear-gradient(rgba(0, 60, 255, 0.05) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255, 0, 60, 0.05) 1px, transparent 1px);
            background-size: 30px 30px;
            pointer-events: none;
            z-index: 0;
            animation: ledPulse 4s ease-in-out infinite;
        }
        
        @keyframes ledPulse {
            0%, 100% { opacity: 0.3; }
            50% { opacity: 0.6; }
        }
        
        /* Pyramid Title */
        .pyramid-container {
            position: relative;
            text-align: center;
            margin: 2rem 0;
            perspective: 1000px;
        }
        
        .pyramid {
            width: 0;
            height: 0;
            border-left: 150px solid transparent;
            border-right: 150px solid transparent;
            border-bottom: 200px solid rgba(0, 60, 255, 0.2);
            margin: 0 auto 2rem;
            position: relative;
            animation: pyramidGlow 3s ease-in-out infinite;
            filter: drop-shadow(0 0 30px rgba(0, 60, 255, 0.8));
        }
        
        .pyramid::before {
            content: "";
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 0;
            height: 0;
            border-left: 130px solid transparent;
            border-right: 130px solid transparent;
            border-bottom: 180px solid rgba(255, 0, 60, 0.3);
            filter: drop-shadow(0 0 20px rgba(255, 0, 60, 0.6));
        }
        
        @keyframes pyramidGlow {
            0%, 100% {
                filter: drop-shadow(0 0 30px rgba(0, 60, 255, 0.8)) drop-shadow(0 0 50px rgba(255, 0, 60, 0.4));
            }
            50% {
                filter: drop-shadow(0 0 50px rgba(0, 60, 255, 1)) drop-shadow(0 0 70px rgba(255, 0, 60, 0.8));
            }
        }
        
        /* LED Strips */
        .led-strip {
            height: 3px;
            margin: 1rem 0;
            background: linear-gradient(90deg, 
                transparent 0%, 
                #003cff 20%, 
                #ff003c 50%, 
                #003cff 80%, 
                transparent 100%);
            box-shadow: 
                0 0 10px rgba(0, 60, 255, 0.8),
                0 0 20px rgba(255, 0, 60, 0.8);
            animation: ledRun 3s linear infinite;
        }
        
        @keyframes ledRun {
            0% { background-position: 0% 50%; }
            100% { background-position: 200% 50%; }
        }
        
        /* Title Styling */
        h1 {
            font-family: 'Orbitron', monospace;
            font-weight: 900;
            font-size: 4rem !important;
            text-align: center;
            background: linear-gradient(135deg, #003cff 0%, #ff003c 50%, #003cff 100%);
            background-size: 200% 200%;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-transform: uppercase;
            letter-spacing: 0.5rem;
            margin: 1rem 0;
            animation: aliveGradient 4s ease infinite;
            filter: drop-shadow(0 0 20px rgba(0, 60, 255, 0.8));
        }
        
        @keyframes aliveGradient {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        
        /* Subtitle */
        .subtitle {
            text-align: center;
            color: #00d4ff;
            font-size: 1.4rem;
            letter-spacing: 0.3rem;
            margin-bottom: 2rem;
            text-transform: uppercase;
            font-weight: 700;
            text-shadow: 0 0 15px rgba(0, 212, 255, 0.8);
            animation: textPulse 2s ease-in-out infinite;
        }
        
        @keyframes textPulse {
            0%, 100% { opacity: 0.8; }
            50% { opacity: 1; text-shadow: 0 0 25px rgba(0, 212, 255, 1); }
        }
        
        /* File Uploader */
        .stFileUploader {
            background: linear-gradient(145deg, rgba(0, 0, 0, 0.8), rgba(10, 20, 50, 0.8));
            border: 2px solid #003cff;
            border-radius: 15px;
            padding: 2rem;
            box-shadow: 
                0 0 30px rgba(0, 60, 255, 0.4),
                inset 0 0 20px rgba(255, 0, 60, 0.1);
            position: relative;
            overflow: hidden;
        }
        
        .stFileUploader::before {
            content: "";
            position: absolute;
            top: -2px;
            left: -2px;
            right: -2px;
            bottom: -2px;
            background: linear-gradient(90deg, #003cff, #ff003c, #003cff);
            background-size: 200% 100%;
            border-radius: 15px;
            z-index: -1;
            animation: borderFlow 3s linear infinite;
            opacity: 0.5;
        }
        
        @keyframes borderFlow {
            0% { background-position: 0% 50%; }
            100% { background-position: 200% 50%; }
        }
        
        .stFileUploader label {
            color: #00d4ff !important;
            font-size: 1.2rem !important;
            font-weight: 700 !important;
            text-transform: uppercase;
            letter-spacing: 0.15rem;
            text-shadow: 0 0 10px rgba(0, 212, 255, 0.8);
        }
        
        /* Radio Buttons */
        .stRadio > label {
            color: #00d4ff !important;
            font-size: 1.2rem !important;
            font-weight: 700 !important;
            text-transform: uppercase;
            letter-spacing: 0.15rem;
            text-shadow: 0 0 10px rgba(0, 212, 255, 0.8);
        }
        
        .stRadio > div {
            background: linear-gradient(145deg, rgba(0, 0, 0, 0.8), rgba(10, 20, 50, 0.8));
            border: 2px solid #ff003c;
            border-radius: 15px;
            padding: 1.5rem;
            box-shadow: 
                0 0 30px rgba(255, 0, 60, 0.4),
                inset 0 0 20px rgba(0, 60, 255, 0.1);
        }
        
        .stRadio > div > label {
            background: linear-gradient(90deg, rgba(0, 60, 255, 0.15), rgba(255, 0, 60, 0.15));
            border: 1px solid rgba(0, 212, 255, 0.5);
            border-radius: 10px;
            padding: 1rem;
            margin: 0.5rem 0;
            cursor: pointer;
            transition: all 0.3s ease;
            font-weight: 600;
        }
        
        .stRadio > div > label:hover {
            background: linear-gradient(90deg, rgba(0, 60, 255, 0.3), rgba(255, 0, 60, 0.3));
            border-color: #00d4ff;
            box-shadow: 
                0 0 20px rgba(0, 212, 255, 0.6),
                0 0 40px rgba(255, 0, 60, 0.3);
            transform: translateX(10px);
        }
        
        /* Success/Error Messages */
        .stSuccess {
            background: linear-gradient(145deg, rgba(0, 60, 255, 0.2), rgba(0, 20, 40, 0.9));
            border: 2px solid #00d4ff;
            border-radius: 10px;
            padding: 1rem;
            color: #00d4ff;
            font-weight: 700;
            box-shadow: 0 0 30px rgba(0, 212, 255, 0.5);
            text-transform: uppercase;
            letter-spacing: 0.1rem;
        }
        
        .stError {
            background: linear-gradient(145deg, rgba(255, 0, 60, 0.2), rgba(40, 0, 20, 0.9));
            border: 2px solid #ff003c;
            border-radius: 10px;
            padding: 1rem;
            color: #ff003c;
            font-weight: 700;
            box-shadow: 0 0 30px rgba(255, 0, 60, 0.5);
            text-transform: uppercase;
            letter-spacing: 0.1rem;
        }
        
        .stSpinner > div {
            border-color: #003cff #ff003c #00d4ff transparent !important;
        }
        
        /* Container */
        .main > div {
            background: rgba(0, 0, 0, 0.6);
            border-radius: 20px;
            padding: 2rem;
            backdrop-filter: blur(10px);
            box-shadow: 
                0 0 50px rgba(0, 60, 255, 0.2),
                0 0 100px rgba(255, 0, 60, 0.1);
            border: 1px solid rgba(0, 212, 255, 0.2);
            position: relative;
            z-index: 1;
        }
        
        /* Concert Lights Effect */
        .concert-lights {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 0;
        }
        
        .light-beam {
            position: absolute;
            width: 2px;
            height: 100%;
            background: linear-gradient(180deg, rgba(0, 60, 255, 0.3), transparent);
            animation: beamSweep 8s ease-in-out infinite;
        }
        
        .light-beam:nth-child(1) { left: 20%; animation-delay: 0s; }
        .light-beam:nth-child(2) { left: 50%; animation-delay: 2s; background: linear-gradient(180deg, rgba(255, 0, 60, 0.3), transparent); }
        .light-beam:nth-child(3) { left: 80%; animation-delay: 4s; }
        
        @keyframes beamSweep {
            0%, 100% { transform: translateX(-50px) scaleY(0.5); opacity: 0.3; }
            50% { transform: translateX(50px) scaleY(1); opacity: 0.7; }
        }
    </style>

    <div class="concert-lights">
        <div class="light-beam"></div>
        <div class="light-beam"></div>
        <div class="light-beam"></div>
    </div>
    """, unsafe_allow_html=True)

else:
    # DISCOVERY METALLIC THEME
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;600;700&family=Orbitron:wght@700;900&family=Space+Grotesk:wght@400;600;700&display=swap');
        
        /* Global Metallic Theme - Discovery 2001 */
        .stApp {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            color: #e0e0e0;
            font-family: 'Space Grotesk', 'Rajdhani', sans-serif;
        }
        
        /* Hide Streamlit branding */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* Metallic Sheen Effect */
        .stApp::before {
            content: "";
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: 
                radial-gradient(ellipse at 20% 30%, rgba(192, 192, 192, 0.08) 0%, transparent 50%),
                radial-gradient(ellipse at 80% 70%, rgba(255, 215, 0, 0.06) 0%, transparent 50%);
            pointer-events: none;
            z-index: 0;
            animation: metallicShift 8s ease-in-out infinite;
        }
        
        @keyframes metallicShift {
            0%, 100% { opacity: 0.4; }
            50% { opacity: 0.7; }
        }
        
        /* Circuit Board Pattern */
        .stApp::after {
            content: "";
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-image: 
                linear-gradient(rgba(192, 192, 192, 0.03) 1px, transparent 1px),
                linear-gradient(90deg, rgba(192, 192, 192, 0.03) 1px, transparent 1px);
            background-size: 40px 40px;
            pointer-events: none;
            z-index: 0;
        }
        
               /* Split Helmet Icon - Daft Punk Style */
      /* Split Helmet Icon - Daft Punk Style */
        .helmet-container {
            position: relative;
            text-align: center;
            margin: 2rem 0;
            perspective: 1200px;
        }
        
        .helmet {
            width: 180px;
            height: 220px;
            margin: 0 auto 1rem;
            position: relative;
            overflow: visible;
            animation: helmetFloat 4s ease-in-out infinite;
            filter: drop-shadow(0 20px 50px rgba(0, 0, 0, 0.6));
        }
        
        /* Silver/Chrome Left Half - Proper helmet shape */
        .helmet::before {
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            width: 50%;
            height: 100%;
            background: linear-gradient(160deg, 
                #ffffff 0%,
                #d4d4d4 15%,
                #a8a8a8 35%,
                #c0c0c0 50%,
                #e8e8e8 70%,
                #b0b0b0 100%);
            clip-path: polygon(
                20% 0%,
                50% 0%,
                50% 35%,
                50% 70%,
                40% 100%,
                10% 90%,
                0% 70%,
                0% 25%
            );
            box-shadow: 
                inset -8px 0 25px rgba(80, 80, 80, 0.4),
                inset 15px 15px 35px rgba(255, 255, 255, 0.3),
                inset -5px -15px 30px rgba(0, 0, 0, 0.25);
        }
        
        /* Gold Right Half - Proper helmet shape */
        .helmet::after {
            content: "";
            position: absolute;
            top: 0;
            right: 0;
            width: 50%;
            height: 100%;
            background: linear-gradient(200deg,
                #ffed4e 0%,
                #ffd700 15%,
                #cc8800 35%,
                #ffaa00 50%,
                #ffd700 70%,
                #cc7700 100%);
            clip-path: polygon(
                50% 0%,
                80% 0%,
                100% 25%,
                100% 70%,
                90% 90%,
                60% 100%,
                50% 70%,
                50% 35%
            );
            box-shadow: 
                inset 8px 0 25px rgba(150, 100, 0, 0.4),
                inset -15px 15px 35px rgba(255, 255, 150, 0.4),
                inset 5px -15px 30px rgba(100, 60, 0, 0.3);
        }
        
        /* Center Divider Line - Vertical seam */
        .helmet-divider {
            position: absolute;
            top: 0;
            left: 50%;
            transform: translateX(-50%);
            width: 4px;
            height: 100%;
            background: linear-gradient(180deg, 
                rgba(20, 20, 20, 0) 0%,
                rgba(40, 40, 40, 0.9) 5%,
                rgba(20, 20, 20, 1) 20%,
                rgba(10, 10, 10, 1) 50%,
                rgba(20, 20, 20, 1) 80%,
                rgba(40, 40, 40, 0.9) 95%,
                rgba(20, 20, 20, 0) 100%);
            box-shadow: 
                0 0 15px rgba(0, 0, 0, 0.8),
                inset 0 0 5px rgba(255, 255, 255, 0.2);
            z-index: 10;
        }
        
        /* Visor Glow Effect - Horizontal LED strip */
        .helmet-visor {
            position: absolute;
            top: 42%;
            left: 50%;
            transform: translateX(-50%);
            width: 70%;
            height: 30px;
            background: linear-gradient(90deg,
                rgba(80, 120, 200, 0.7) 0%,
                rgba(120, 180, 255, 1) 20%,
                rgba(180, 220, 255, 1) 40%,
                rgba(255, 220, 180, 1) 60%,
                rgba(255, 180, 120, 1) 80%,
                rgba(200, 120, 80, 0.7) 100%);
            border-radius: 15px;
            box-shadow: 
                0 0 40px rgba(150, 200, 255, 0.9),
                0 0 20px rgba(255, 180, 120, 0.6),
                inset 0 4px 12px rgba(255, 255, 255, 0.5),
                inset 0 -4px 12px rgba(0, 0, 0, 0.4);
            animation: visorPulse 2.5s ease-in-out infinite;
            z-index: 5;
            clip-path: polygon(
                8% 0%,
                92% 0%,
                100% 50%,
                92% 100%,
                8% 100%,
                0% 50%
            );
        }
        
        /* Chin detail */
        .helmet-chin {
            position: absolute;
            bottom: 10%;
            left: 50%;
            transform: translateX(-50%);
            width: 60%;
            height: 20px;
            background: linear-gradient(90deg,
                rgba(160, 160, 160, 0.5) 0%,
                rgba(120, 120, 120, 0.8) 50%,
                rgba(180, 140, 60, 0.5) 100%);
            border-radius: 0 0 40px 40px;
            box-shadow: 
                inset 0 -3px 10px rgba(0, 0, 0, 0.4);
            z-index: 3;
        }
        
        @keyframes helmetFloat {
            0%, 100% {
                transform: translateY(0px) rotateY(-2deg);
            }
            50% {
                transform: translateY(-8px) rotateY(2deg);
            }
        }
        
        @keyframes visorPulse {
            0%, 100% {
                box-shadow: 
                    0 0 40px rgba(150, 200, 255, 0.9),
                    0 0 20px rgba(255, 180, 120, 0.6),
                    inset 0 4px 12px rgba(255, 255, 255, 0.5);
            }
            50% {
                box-shadow: 
                    0 0 60px rgba(150, 200, 255, 1),
                    0 0 40px rgba(255, 180, 120, 0.9),
                    inset 0 4px 18px rgba(255, 255, 255, 0.7);
            }
        }
        
        /* Title Styling */
        h1 {
            font-family: 'Orbitron', monospace;
            font-weight: 900;
            font-size: 4rem !important;
            text-align: center;
            background: linear-gradient(135deg, #c0c0c0 0%, #ffd700 25%, #ffffff 50%, #ffd700 75%, #c0c0c0 100%);
            background-size: 200% 200%;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-transform: uppercase;
            letter-spacing: 0.5rem;
            margin: 1rem 0;
            animation: metallicFlow 5s ease infinite;
            filter: drop-shadow(0 2px 8px rgba(192, 192, 192, 0.5));
        }
        
        @keyframes metallicFlow {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        
        /* Subtitle */
        .subtitle {
            text-align: center;
            color: #c0c0c0;
            font-size: 1.4rem;
            letter-spacing: 0.3rem;
            margin-bottom: 2rem;
            text-transform: uppercase;
            font-weight: 700;
            text-shadow: 0 2px 8px rgba(192, 192, 192, 0.4);
            animation: subtitlePulse 3s ease-in-out infinite;
        }
        
        @keyframes subtitlePulse {
            0%, 100% { opacity: 0.7; }
            50% { opacity: 1; text-shadow: 0 2px 12px rgba(255, 215, 0, 0.6); }
        }
        
        /* File Uploader */
        .stFileUploader {
            background: linear-gradient(145deg, rgba(30, 30, 50, 0.9), rgba(40, 40, 70, 0.9));
            border: 2px solid #808080;
            border-radius: 15px;
            padding: 2rem;
            box-shadow: 
                0 8px 32px rgba(192, 192, 192, 0.2),
                inset 0 0 20px rgba(100, 100, 100, 0.1);
            position: relative;
            overflow: hidden;
        }
        
        .stFileUploader::before {
            content: "";
            position: absolute;
            top: -2px;
            left: -2px;
            right: -2px;
            bottom: -2px;
            background: linear-gradient(90deg, #808080, #c0c0c0, #ffd700, #c0c0c0, #808080);
            background-size: 300% 100%;
            border-radius: 15px;
            z-index: -1;
            animation: borderChrome 4s linear infinite;
            opacity: 0.5;
        }
        
        @keyframes borderChrome {
            0% { background-position: 0% 50%; }
            100% { background-position: 300% 50%; }
        }
        
        .stFileUploader label {
            color: #d4d4d4 !important;
            font-size: 1.2rem !important;
            font-weight: 700 !important;
            text-transform: uppercase;
            letter-spacing: 0.15rem;
            text-shadow: 0 1px 4px rgba(192, 192, 192, 0.3);
        }
        
        /* Radio Buttons */
        .stRadio > label {
            color: #d4d4d4 !important;
            font-size: 1.2rem !important;
            font-weight: 700 !important;
            text-transform: uppercase;
            letter-spacing: 0.15rem;
            text-shadow: 0 1px 4px rgba(192, 192, 192, 0.3);
        }
        
        .stRadio > div {
            background: linear-gradient(145deg, rgba(30, 30, 50, 0.9), rgba(40, 40, 70, 0.9));
            border: 2px solid #a0a0a0;
            border-radius: 15px;
            padding: 1.5rem;
            box-shadow: 
                0 8px 32px rgba(160, 160, 160, 0.2),
                inset 0 0 20px rgba(100, 100, 100, 0.1);
        }
        
        .stRadio > div > label {
            background: linear-gradient(90deg, rgba(192, 192, 192, 0.1), rgba(255, 215, 0, 0.1));
            border: 1px solid rgba(192, 192, 192, 0.3);
            border-radius: 10px;
            padding: 1rem;
            margin: 0.5rem 0;
            cursor: pointer;
            transition: all 0.3s ease;
            font-weight: 600;
            color: #e0e0e0;
        }
        
        .stRadio > div > label:hover {
            background: linear-gradient(90deg, rgba(192, 192, 192, 0.2), rgba(255, 215, 0, 0.2));
            border-color: #ffd700;
            box-shadow: 
                0 4px 20px rgba(255, 215, 0, 0.3),
                0 8px 40px rgba(192, 192, 192, 0.2);
            transform: translateX(10px);
        }
        
        /* Success/Error Messages */
        .stSuccess {
            background: linear-gradient(145deg, rgba(192, 192, 192, 0.2), rgba(30, 50, 30, 0.9));
            border: 2px solid #90ee90;
            border-radius: 10px;
            padding: 1rem;
            color: #90ee90;
            font-weight: 700;
            box-shadow: 0 4px 20px rgba(144, 238, 144, 0.3);
            text-transform: uppercase;
            letter-spacing: 0.1rem;
        }
        
        .stError {
            background: linear-gradient(145deg, rgba(192, 192, 192, 0.2), rgba(50, 30, 30, 0.9));
            border: 2px solid #ff6b6b;
            border-radius: 10px;
            padding: 1rem;
            color: #ff6b6b;
            font-weight: 700;
            box-shadow: 0 4px 20px rgba(255, 107, 107, 0.3);
            text-transform: uppercase;
            letter-spacing: 0.1rem;
        }
        
        .stSpinner > div {
            border-color: #c0c0c0 #ffd700 #808080 transparent !important;
        }
        
        /* Container */
        .main > div {
            background: rgba(26, 26, 46, 0.7);
            border-radius: 20px;
            padding: 2rem;
            backdrop-filter: blur(10px);
            box-shadow: 
                0 8px 40px rgba(192, 192, 192, 0.15),
                0 16px 80px rgba(255, 215, 0, 0.1);
            border: 1px solid rgba(192, 192, 192, 0.2);
            position: relative;
            z-index: 1;
        }
        
        /* Floating Particles Effect */
        .particle-field {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 0;
        }
        
        .particle {
            position: absolute;
            width: 3px;
            height: 3px;
            background: radial-gradient(circle, #c0c0c0, transparent);
            border-radius: 50%;
            animation: particleFloat 6s ease-in-out infinite;
        }
        
        .particle:nth-child(1) { top: 15%; left: 20%; animation-delay: 0s; }
        .particle:nth-child(2) { top: 35%; left: 75%; animation-delay: 1.5s; }
        .particle:nth-child(3) { top: 55%; left: 30%; animation-delay: 3s; }
        .particle:nth-child(4) { top: 75%; left: 65%; animation-delay: 4.5s; }
        .particle:nth-child(5) { top: 25%; left: 50%; animation-delay: 2s; }
        
        @keyframes particleFloat {
            0%, 100% { opacity: 0.3; transform: translateY(0) scale(1); }
            50% { opacity: 0.8; transform: translateY(-20px) scale(1.3); box-shadow: 0 0 15px #c0c0c0; }
        }
    </style>

    <div class="particle-field">
        <div class="particle"></div>
        <div class="particle"></div>
        <div class="particle"></div>
        <div class="particle"></div>
        <div class="particle"></div>
    </div>
    """, unsafe_allow_html=True)

# ==================== HEADER ====================
if st.session_state.theme == "Alive 2007":
    st.markdown("""
    <div class="pyramid-container">
        <div class="pyramid"></div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('# AutoMap')
    st.markdown('<div class="subtitle">◢ Alive 2007 • Paris • Bercy ◣</div>', unsafe_allow_html=True)
    st.markdown('<div class="led-strip"></div>', unsafe_allow_html=True)
else:
    st.markdown("""
    <div class="helmet-container">
        <div class="helmet"></div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('# AutoMap')
    st.markdown('<div class="subtitle">✦ Discovery 2001 • One More Time ✦</div>', unsafe_allow_html=True)
    st.markdown('<div class="chrome-strip"></div>', unsafe_allow_html=True)

# ==================== FUNCTIONS ====================
def extract_text(filepath: str) -> str:
    file_path = Path(filepath)
    text = ""
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    if file_path.suffix.lower() == ".pdf":
        import fitz   
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            pagetext = page.get_text("text")
            if isinstance(pagetext, str):
                text += pagetext
            elif isinstance(pagetext, list):
                text += "".join(map(str, pagetext))
            elif isinstance(pagetext, dict):
                text += str(pagetext)    
        doc.close()
        return text    
    elif file_path.suffix.lower() == ".docx":
        from docx import Document
        doc = Document(filepath)
        return "\n".join(paragraph.text for paragraph in doc.paragraphs)
    else:
        raise ValueError("Unsupported file type")

    return text

import google.generativeai as genai

def generate_gemini_mindmap(text: str) -> str:
    if not text or not text.strip():
        raise ValueError("Input text is empty.")

    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = f"""Create a hierarchical mind map of the following document.
Use a nested bullet list with dashes (-) and 2-space indentation per level.
Limit depth to 3 levels. Only output the mind map.make a big mind map and also make SURE its kind of interconnected.if not interconnected there is ZERO USE.

Document:
{text[:12000]}
"""

    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(max_output_tokens=1048576),
        safety_settings=[
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ],
    )

    output = []
    if getattr(response, "candidates", None):
        for c in response.candidates:
            if getattr(c, "content", None) and getattr(c.content, "parts", None):
                for p in c.content.parts:
                    if hasattr(p, "text"):
                        output.append(p.text)

    if output:
        return "\n".join(output).strip()

    finish_reasons = [getattr(c, "finish_reason", None) for c in getattr(response, "candidates", [])]
    raise RuntimeError(f"No text returned. Finish reasons: {finish_reasons}.")

def parse_bullet_mindmap(bullet_text: str):
    lines = bullet_text.strip().split('\n')
    stack = []
    root = []

    for line in lines:
        if not line.strip():
            continue

        raw_line = line
        content = raw_line.lstrip(' ')
        if not content.startswith('- '):
            continue  
        content = content[2:].strip() 

        leading_spaces = len(raw_line) - len(raw_line.lstrip(' '))
        depth = leading_spaces // 2  

        node = {'title': content, 'children': []}

        while stack and stack[-1][1] >= depth:
            stack.pop()

        if depth == 0:
            root.append(node)
            stack = [(node, depth)]
        else:
            if stack:
                parent = stack[-1][0]
                parent['children'].append(node)
            stack.append((node, depth))

    return root

def generate_clustering_mindmap(text: str, min_cluster_size: int = 3):
    import re
    from sentence_transformers import SentenceTransformer
    import umap
    import hdbscan
    import numpy as np

    sentences = re.split(r'(?<=[.!?])\s+', text)
    sentences = [s.strip() for s in sentences if 20 < len(s.strip()) < 500]

    if len(sentences) < 5:
        sentences = [p.strip() for p in text.split('\n') if len(p.strip()) > 30]
    if len(sentences) < 2:
        sentences = [text[i:i+300] for i in range(0, len(text), 300)][:20]

    if not sentences:
        return [{"title": "Clustering failed", "children": []}]

    model = SentenceTransformer('all-MiniLM-L6-v2')
    embeddings = model.encode(sentences, show_progress_bar=False)

    umap_model = umap.UMAP(n_neighbors=5, n_components=5, random_state=42)
    umap_embeds = umap_model.fit_transform(embeddings)

    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=1,
        metric='euclidean',
        cluster_selection_method='leaf'
    )
    clusters = clusterer.fit_predict(umap_embeds)

    unique_clusters = sorted(set(clusters))
    root_nodes = []

    for cluster_id in unique_clusters:
        if cluster_id == -1:
            continue

        members = [sentences[i] for i, c in enumerate(clusters) if c == cluster_id]
        if not members:
            continue

        label = " ".join(members[0].split()[:6])
        if len(members[0].split()) > 6:
            label += "..."

        children = []
        for m in members[:4]:
            short = (m[:70] + "...") if len(m) > 70 else m
            children.append({"title": short, "children": []})

        root_nodes.append({
            "title": f"Topic {cluster_id}: {label}",
            "children": children
        })

    if not root_nodes:
        return [{"title": "Single Topic", "children": [{"title": t[:70], "children": []} for t in sentences[:5]]}]

    return root_nodes

from pyvis.network import Network

def tree_to_pyvis(tree_data, height="1000px", width="100%", theme="dark"):
    if theme == "dark":
        # Alive 2007 theme - Claude-style grey background
        bg_color = "#2f2f2f"
        font_color = "#e8e8e8"
        node_colors = {
            0: {"border": "#5a9fd4", "background": "#3a3a4a", 
                "highlight": {"border": "#7ab8e8", "background": "#4a4a5a"}},
            1: {"border": "#9a7fd4", "background": "#3a3a4a", 
                "highlight": {"border": "#b49fe8", "background": "#4a4a5a"}},
            2: {"border": "#7fd49a", "background": "#3a3a4a", 
                "highlight": {"border": "#9fe8b4", "background": "#4a4a5a"}}
        }
        edge_colors = {1: "#6a9fd4", 2: "#8a7fd4", "default": "#7fd48a"}
        shadow_color = "rgba(90, 159, 212, 0.2)"
        font_size = 16
        border_width = 2
    else:
        # Discovery theme - Metallic grey/chrome aesthetic
        bg_color = "#2a2a3e"
        font_color = "#d4d4d4"
        node_colors = {
            0: {"border": "#a0a0a0", "background": "#3a3a52", 
                "highlight": {"border": "#c0c0c0", "background": "#4a4a62"}},
            1: {"border": "#b0b0b0", "background": "#3a3a52", 
                "highlight": {"border": "#d0d0d0", "background": "#4a4a62"}},
            2: {"border": "#c8a850", "background": "#3a3a52", 
                "highlight": {"border": "#e0c060", "background": "#4a4a62"}}
        }
        edge_colors = {1: "#a8a8a8", 2: "#b8b8b8", "default": "#c8a850"}
        shadow_color = "rgba(192, 192, 192, 0.25)"
        font_size = 16
        border_width = 2
    
    net = Network(height=height, width=width, bgcolor=bg_color, font_color=font_color, directed=True)
    net.set_options(f"""
    {{
      "nodes": {{
        "shape": "box",
        "font": {{"size": {font_size}, "face": "Rajdhani", "color": "{font_color}", "bold": true}},
        "margin": 14,
        "widthConstraint": {{"maximum": 350}},
        "borderWidth": {border_width},
        "shadow": {{"enabled": true, "color": "{shadow_color}", "size": 10, "x": 0, "y": 0}}
      }},
      "edges": {{
        "arrows": {{"to": {{"enabled": true, "scaleFactor": 0.6}}}},
        "smooth": {{"type": "cubicBezier", "roundness": 0.4}},
        "width": 2,
        "shadow": {{"enabled": true, "color": "{shadow_color}", "size": 6}}
      }},
      "interaction": {{
        "hover": true,
        "tooltipDelay": 100,
        "navigationButtons": true,
        "keyboard": true,
        "zoomView": true
      }},
      "physics": {{
        "enabled": true,
        "barnesHut": {{
          "gravitationalConstant": -8000,
          "centralGravity": 0.3,
          "springLength": 150,
          "springConstant": 0.04,
          "damping": 0.35,
          "avoidOverlap": 0.8
        }},
        "stabilization": {{
          "iterations": 250,
          "updateInterval": 25
        }}
      }}
    }}
    """)

    node_id_counter = [0]  

    def add_node(parent_id, node_dict, depth=0):
        node_id = f"node_{node_id_counter[0]}"
        node_id_counter[0] += 1
        display_title = node_dict['title'][:60] + "..." if len(node_dict['title']) > 60 else node_dict['title']
        
        color = node_colors.get(depth, node_colors[2])
            
        net.add_node(
            node_id,
            label=display_title,
            title=node_dict['title'],
            color=color,
            size=30 + depth * 3
        )
        
        if parent_id:
            edge_color = edge_colors.get(depth, edge_colors["default"])
            net.add_edge(parent_id, node_id, color=edge_color)
            
        for child in node_dict.get('children', []):
            add_node(node_id, child, depth + 1)

    for root in tree_data:
        add_node(None, root, 0)

    return net

# ==================== MAIN APP ====================
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    uploaded_file = st.file_uploader("📁 UPLOAD DOCUMENT", type=["pdf", "docx"])
    
if st.session_state.theme == "Alive 2007":
    st.markdown('<div class="led-strip"></div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="chrome-strip"></div>', unsafe_allow_html=True)

option = st.radio(
    "⚡ SELECT MODE:",
    ("🎯 Human After All", "🚀 Discovery")
)

if st.session_state.theme == "Alive 2007":
    st.markdown('<div class="led-strip"></div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="chrome-strip"></div>', unsafe_allow_html=True)

if uploaded_file is not None:
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=uploaded_file.name) as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name

        with st.spinner('🔄 PROCESSING... ONE MORE TIME...'):
            text = extract_text(tmp_path)

            if option == "🎯 Human After All":
                raw_map = generate_gemini_mindmap(text)
                tree = parse_bullet_mindmap(raw_map)
            else:
                tree = generate_clustering_mindmap(text)

            theme_type = "dark" if st.session_state.theme == "Alive 2007" else "light"
            net = tree_to_pyvis(tree, theme=theme_type)
            output = "mindmap.html"
            net.save_graph(output)

        if st.session_state.theme == "Alive 2007":
            st.success("✅ SYSTEM READY • REVOLUTION 909")
        else:
            st.success("✅ SYSTEM READY • DIGITAL LOVE")
        
        with open(output, "r", encoding="utf-8") as f:
            html = f.read()
        st.components.v1.html(html, height=1000, scrolling=True)

        os.unlink(tmp_path)
        os.unlink(output)

    except Exception as e:
        st.error(f"❌ ERROR • CONTACT: {e}")
else:
    if st.session_state.theme == "Alive 2007":
        st.info("👆 Upload document to start • DA FUNK")
    else:
        st.info("👆 Upload document to start • AERODYNAMIC")

if st.session_state.theme == "Alive 2007":
    st.markdown('<div class="led-strip"></div>', unsafe_allow_html=True)
    st.markdown('<div style="text-align: center; color: #00d4ff; font-size: 1.1rem; letter-spacing: 0.3rem; text-shadow: 0 0 15px rgba(0, 212, 255, 0.8);">◢ ROBOT ROCK ◣</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="chrome-strip"></div>', unsafe_allow_html=True)
    st.markdown('<div style="text-align: center; color: #c0c0c0; font-size: 1.1rem; letter-spacing: 0.3rem; text-shadow: 0 2px 6px rgba(192, 192, 192, 0.5);">✦ HARDER BETTER FASTER STRONGER ✦</div>', unsafe_allow_html=True)