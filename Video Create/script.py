import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from PIL import Image, ImageDraw, ImageFont
import os
import re
import glob
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import pyaudio
import wave
from pydub import AudioSegment
from pydub.silence import split_on_silence, detect_nonsilent
import time
import threading


class SubtitleTTSGeneratorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("자막 및 음성 생성기")
        self.root.geometry("800x600")

        # 변수 초기화
        self.input_file = tk.StringVar()
        self.output_folder = tk.StringVar()
        self.font_size = tk.StringVar(value="24")

        # 고정 TTS 설정
        self.CHARS_PER_SECOND = 6
        self.ADDITIONAL_DELAY = 1

        # 녹음 관련 설정
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 2
        self.RATE = 44100

        # GUI 구성
        self.create_widgets()

    def create_widgets(self):
        # 스타일 설정
        style = ttk.Style()
        style.configure('TButton', padding=5)
        style.configure('TLabel', padding=5)

        # 입력 파일 선택
        input_frame = ttk.LabelFrame(self.root, text="입력 설정", padding=10)
        input_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(input_frame, text="대본 파일:").pack(anchor='w')
        input_file_frame = ttk.Frame(input_frame)
        input_file_frame.pack(fill='x')
        ttk.Entry(input_file_frame, textvariable=self.input_file).pack(side='left', fill='x', expand=True)
        ttk.Button(input_file_frame, text="찾아보기", command=self.browse_input_file).pack(side='right', padx=5)

        # 출력 폴더 선택
        output_frame = ttk.LabelFrame(self.root, text="출력 설정", padding=10)
        output_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(output_frame, text="출력 폴더:").pack(anchor='w')
        output_folder_frame = ttk.Frame(output_frame)
        output_folder_frame.pack(fill='x')
        ttk.Entry(output_folder_frame, textvariable=self.output_folder).pack(side='left', fill='x', expand=True)
        ttk.Button(output_folder_frame, text="찾아보기", command=self.browse_output_folder).pack(side='right', padx=5)

        # 설정 프레임
        settings_frame = ttk.LabelFrame(self.root, text="설정", padding=10)
        settings_frame.pack(fill='x', padx=10, pady=5)

        # 폰트 설정
        ttk.Label(settings_frame, text="폰트 크기:").pack(side='left')
        ttk.Entry(settings_frame, textvariable=self.font_size, width=10).pack(side='left', padx=5)

        # 실행 버튼
        button_frame = ttk.Frame(self.root)
        button_frame.pack(pady=20)
        ttk.Button(button_frame, text="자막 생성", command=self.generate_subtitles).pack(side='left', padx=5)
        ttk.Button(button_frame, text="음성 생성", command=self.generate_tts).pack(side='left', padx=5)
        ttk.Button(button_frame, text="자막 및 음성 생성", command=self.generate_both).pack(side='left', padx=5)

        # 진행 상황 표시
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.root, length=300, mode='determinate', variable=self.progress_var)
        self.progress_bar.pack(pady=5)

        self.status_label = ttk.Label(self.root, text="")
        self.status_label.pack(pady=5)

    def browse_input_file(self):
        filename = filedialog.askopenfilename(
            title="대본 파일 선택",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            self.input_file.set(filename)
            self.output_folder.set(os.path.dirname(filename))

    def browse_output_folder(self):
        folder = filedialog.askdirectory(title="출력 폴더 선택")
        if folder:
            self.output_folder.set(folder)

    def sanitize_filename(self, filename):
        return re.sub(r'[\\/*?:"<>|]', "_", filename)

    def delete_all_png_files(self, folder_path):
        for file_path in glob.glob(os.path.join(folder_path, '*.png')):
            os.remove(file_path)

    def remove_silence_with_padding(self, input_path, output_path):
        audio = AudioSegment.from_wav(input_path)
        silence_thresh = -40
        min_silence_len = 100

        nonsilent_ranges = detect_nonsilent(
            audio,
            min_silence_len=min_silence_len,
            silence_thresh=silence_thresh
        )

        if nonsilent_ranges:
            start_trim = max(0, nonsilent_ranges[0][0] - 100)
            end_trim = min(len(audio), nonsilent_ranges[-1][1] + 300)
            trimmed_audio = audio[start_trim:end_trim]
            trimmed_audio = trimmed_audio.fade_out(50)
            trimmed_audio.export(output_path, format="wav")
        else:
            audio.export(output_path, format="wav")

    def generate_subtitles(self):
        try:
            input_file = self.input_file.get()
            output_folder = self.output_folder.get()
            font_size = int(self.font_size.get())

            if not input_file or not output_folder:
                messagebox.showerror("오류", "입력 파일과 출력 폴더를 모두 선택해주세요.")
                return

            try:
                font = ImageFont.truetype("NoonnuBasicGothicRegular.ttf", font_size)
            except IOError:
                font = ImageFont.load_default()

            if not os.path.exists(output_folder):
                os.makedirs(output_folder)
            else:
                self.delete_all_png_files(output_folder)

            with open(input_file, 'r', encoding='utf-8') as file:
                lines = file.readlines()

            total_lines = len([line for line in lines if line.strip()])

            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue

                temp_image = Image.new('RGB', (100, 100), color=(192, 192, 192))
                temp_draw = ImageDraw.Draw(temp_image)
                bbox = temp_draw.textbbox((0, 0), line, font=font)

                width = bbox[2] - bbox[0]
                height = bbox[3] - bbox[1]

                image = Image.new('RGB', (width + 20, height + 30), color=(255, 255, 255))
                draw = ImageDraw.Draw(image)
                draw.text((10, 10), line, font=font, fill=(0, 0, 102))

                sanitized_line = self.sanitize_filename(line)
                output_path = os.path.join(output_folder, f'{i + 1}_{sanitized_line}.png')
                image.save(output_path)

                self.progress_var.set((i + 1) / total_lines * 100)
                self.status_label.config(text=f"자막 생성 중... ({i + 1}/{total_lines})")
                self.root.update()

            self.status_label.config(text="자막 생성이 완료되었습니다!")
            messagebox.showinfo("완료", "자막 생성이 완료되었습니다!")

        except Exception as e:
            messagebox.showerror("오류", f"오류가 발생했습니다: {str(e)}")
            self.status_label.config(text="오류가 발생했습니다.")

    def generate_tts(self):
        try:
            input_file = self.input_file.get()
            output_folder = self.output_folder.get()

            if not input_file or not output_folder:
                messagebox.showerror("오류", "입력 파일과 출력 폴더를 모두 선택해주세요.")
                return

            # 크롬 드라이버 설정
            options = webdriver.ChromeOptions()
            driver = webdriver.Chrome(options=options)
            driver.get('https://papago.naver.com/?sk=ko&tk=en')

            with open(input_file, 'r', encoding='utf-8') as file:
                sentences = file.read().split('\n')

            p = pyaudio.PyAudio()
            time.sleep(3)

            total_sentences = len([s for s in sentences if s.strip()])

            for i, sentence in enumerate(sentences, start=1):
                if not sentence.strip():
                    continue

                input_box = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="txtSource"]')))
                input_box.clear()
                input_box.send_keys(sentence)
                time.sleep(2)

                RECORD_SECONDS = len(sentence) / self.CHARS_PER_SECOND + self.ADDITIONAL_DELAY
                frames = []

                button = driver.find_element(By.XPATH, '//*[@id="btn-toolbar-source"]/span[1]')
                button.click()

                stream = p.open(format=self.FORMAT,
                                channels=self.CHANNELS,
                                rate=self.RATE,
                                input=True,
                                frames_per_buffer=self.CHUNK)

                for _ in range(0, int(self.RATE / self.CHUNK * RECORD_SECONDS)):
                    data = stream.read(self.CHUNK)
                    frames.append(data)

                stream.stop_stream()
                stream.close()

                cleaned_sentence = ''.join(e for e in sentence if e.isalnum())
                if len(cleaned_sentence) > 15:
                    cleaned_sentence = cleaned_sentence[:15]

                temp_filename = os.path.join(output_folder, f"temp_tts{i}_{cleaned_sentence}.wav")
                final_filename = os.path.join(output_folder, f"tts{i}_{cleaned_sentence}.wav")

                wf = wave.open(temp_filename, 'wb')
                wf.setnchannels(self.CHANNELS)
                wf.setsampwidth(p.get_sample_size(self.FORMAT))
                wf.setframerate(self.RATE)
                wf.writeframes(b''.join(frames))
                wf.close()

                self.remove_silence_with_padding(temp_filename, final_filename)
                os.remove(temp_filename)

                self.progress_var.set(i / total_sentences * 100)
                self.status_label.config(text=f"음성 생성 중... ({i}/{total_sentences})")
                self.root.update()

            driver.quit()
            p.terminate()

            self.status_label.config(text="음성 생성이 완료되었습니다!")
            messagebox.showinfo("완료", "음성 생성이 완료되었습니다!")

        except Exception as e:
            messagebox.showerror("오류", f"오류가 발생했습니다: {str(e)}")
            self.status_label.config(text="오류가 발생했습니다.")
            if 'driver' in locals():
                driver.quit()
            if 'p' in locals():
                p.terminate()

    def generate_both(self):
        self.generate_subtitles()
        self.generate_tts()

def main():
    root = tk.Tk()
    app = SubtitleTTSGeneratorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()