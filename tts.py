import subprocess  # Spawns and manages external processes (Piper TTS CLI)
import os  # Provides operating system file and path utilities
import winsound  # Native Windows audio playback library for WAV files
import wave  # Built-in module for reading WAV file headers and frame properties
import threading  # Threading utilities for asynchronous execution and timer callbacks

is_playing = False  # Global boolean flag tracking whether audio is currently playing

def get_audio_duration(file_path):
    """
    Reads a WAV file and calculates its total playback duration in seconds.
    Used to schedule UI status updates the moment speech concludes.
    """
    try:
        if os.path.exists(file_path):  # Verify the audio file exists on disk
            with wave.open(file_path, "rb") as wf:  # Open the WAV file in binary read mode
                frames = wf.getnframes()  # Read total audio frame count
                rate = wf.getframerate()  # Read audio sample rate (frames per second)
                if rate > 0:  # Guard against division by zero
                    return frames / float(rate)  # Return duration in seconds
    except Exception:
        pass  # If reading fails, ignore and return default
    return 0.0  # Return zero if file is missing or unreadable

def stop_speech():
    """
    Immediately stops any currently playing audio and releases the WAV file lock.
    """
    global is_playing  # Access the shared playback status flag
    try:
        winsound.PlaySound(None, winsound.SND_PURGE)  # Halt all active sounds in Windows mixer
    except Exception:
        pass  # Ignore errors if no sound was playing
    is_playing = False  # Reset playback status to idle

def speak(text, on_start=None, on_finish=None, async_mode=False):
    """
    Synthesizes and speaks text using the Piper TTS engine.
    Supports start synchronization callback and completion timer callback.
    """
    global is_playing  # Access the global playback flag

    def _run():
        global is_playing  # Modify playback flag inside inner function
        clean_text = text.replace('"', '').replace("'", "").strip()  # Sanitize quotes and trim whitespace
        if not clean_text:  # If text is empty after cleaning
            if on_start:
                on_start()  # Trigger start callback so UI does not hang
            if on_finish:
                on_finish()  # Trigger finish callback
            return  # Exit without synthesizing empty text

        output_wav = "output.wav"  # Destination filename for generated WAV audio
        model_path = "en_US-danny-low.onnx"  # Local Piper ONNX voice model file

        try:
            stop_speech()  # Stop any previous sound to release file locks on Windows

            # Launch Piper CLI subprocess to synthesize audio from stdin to output file
            process = subprocess.Popen(
                ["piper", "--model", model_path, "--output_file", output_wav],  # Subprocess command arguments
                stdin=subprocess.PIPE,  # Input pipe to send text
                stdout=subprocess.PIPE,  # Output pipe for stdout logs
                stderr=subprocess.PIPE,  # Output pipe for error logs
                text=True,  # Handle streams as text rather than bytes
                encoding="utf-8"  # Ensure UTF-8 character encoding
            )
            process.communicate(input=clean_text)  # Pipe text into Piper and wait for completion

            if on_start:
                on_start()  # Invoke callback the exact millisecond audio file is ready

            if os.path.exists(output_wav):  # Verify the output WAV was successfully generated
                duration = get_audio_duration(output_wav)  # Calculate total duration in seconds
                is_playing = True  # Mark audio state as actively playing
                winsound.PlaySound(output_wav, winsound.SND_FILENAME | winsound.SND_ASYNC)  # Play sound asynchronously

                if on_finish and duration > 0:  # Schedule completion callback if requested
                    timer = threading.Timer(duration, lambda: _handle_finish(on_finish))  # Timer matching audio duration
                    timer.daemon = True  # Ensure timer thread does not prevent program exit
                    timer.start()  # Start the countdown timer

        except Exception as e:
            print(f"TTS Error: {e}")  # Print debug error message
            is_playing = False  # Reset playing state flag
            if on_start:
                on_start()  # Still invoke start callback to render UI text
            if on_finish:
                on_finish()  # Invoke finish callback to reset status

    def _handle_finish(cb):
        """Internal callback handler invoked when the audio playback duration expires."""
        global is_playing  # Access the global playback flag
        is_playing = False  # Mark state as idle
        try:
            cb()  # Invoke the user-supplied finish callback
        except Exception:
            pass  # Suppress any callback execution exceptions

    if async_mode:
        threading.Thread(target=_run, daemon=True).start()  # Run in background daemon thread if requested
    else:
        _run()  # Run synchronously in the current thread

if __name__ == "__main__":
    speak("Jarvis voice system is online.")  # Run test utterance when executed directly