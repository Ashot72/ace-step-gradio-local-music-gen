#### 🚀 ACE-Step 1.5 Local AI Music Generation App on XPU (Intel GPU)

The project runs on Intel GPUs using PyTorch’s XPU support.

A local music generation project built on ACE-Step 1.5 with a lightweight Gradio interface. It allows users to generate music on their own machine instead of relying on cloud services like Suno, giving more privacy, control, and flexibility for experimentation.

The system supports song titles, style tags, duration control, and lyrics with structured formats like verse and chorus. 

The backend uses ACE-Step’s full pipeline, including a planner LLM, diffusion transformer (DiT), text embeddings, and a VAE decoder to convert structured prompts into audio. The project also includes a Windows setup script that installs dependencies, sets up a virtual environment, and downloads model checkpoints (~10GB).

The generated traks are saved in the output folder.

#### 🎤 Audio2Audio Extension (Speech-Based Generation)

I extended the app with an Audio2Audio feature. You can now upload or record a reference audio clip to guide generation—not just rely on text prompts.

A new control, “Refer audio strength” (0–1), determines how strongly the output follows the reference audio versus your tags and lyrics:



![ACE-Step](ACE-step-1.5.png)

#### 👉 Links & Resources
- [ACE-Step/Ace-Step1.5](https://huggingface.co/ACE-Step/Ace-Step1.5)
- [Gradio Web Interface](https://www.gradio.app/)

---


#### 🚀 Clone and Run

```bash
# Clone the repository
git clone https://github.com/Ashot72/ace-step-gradio-local-music-gen
cd ace-step-gradio-local-music-gen

# First-time setup
setup.bat

# Start the app
run.bat

# The app will be available at http://127.0.0.1:7860
```
🛠 Debugging in VS Code 

Install Microsoft’s [Python Debugger](https://marketplace.visualstudio.com/items?itemName=ms-python.debugpy) extension 

Open the Run view (View → Run or Ctrl+Shift+D) to access the debug configuration

📺 **Video (Music Generation)** [Watch on YouTube](https://youtu.be/Bi1mNCWind8) 

📺 **Video (Audio2Audio)** [Watch on YouTube](https://youtu.be/_mPnARfiBCc) 