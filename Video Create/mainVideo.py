import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import cv2
import numpy as np
from PIL import Image
import threading
import wave
from datetime import datetime


class VideoMakerApp:
    def __init__(self, root):
        self.root = root
        self.root.title('영상 제작 프로그램')
        self.root.geometry('800x500')  # 창 크기 증가

        self.main_img_path = r'C:\Users\ska00\Desktop\news\img'
        self.subtitle_path = r'C:\Users\ska00\Desktop\news\voice'
        self.audio_path = r'C:\Users\ska00\Desktop\news\voice'
        self.side_video_path = r'C:\Users\ska00\Desktop\news\output_comments.mp4'

        self.create_widgets()
        self.update_initial_labels()

    def update_initial_labels(self):
        """초기 경로 라벨 업데이트"""
        if os.path.exists(self.main_img_path):
            self.main_img_label.config(text=f'메인 이미지 폴더: {self.main_img_path}')
        if os.path.exists(self.subtitle_path):
            self.subtitle_label.config(text=f'자막 이미지 폴더: {self.subtitle_path}')
        if os.path.exists(self.audio_path):
            self.audio_label.config(text=f'음성 파일 폴더: {self.audio_path}')
        if self.side_video_path:
            self.side_video_label.config(text=f'사이드 영상: {self.side_video_path}')

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        ttk.Button(main_frame, text='메인 이미지 폴더 선택',
                   command=lambda: self.select_folder('main')).grid(row=0, column=0, pady=5, sticky=tk.W)
        self.main_img_label = ttk.Label(main_frame, text='메인 이미지 폴더: 선택되지 않음')
        self.main_img_label.grid(row=1, column=0, pady=5, sticky=tk.W)

        ttk.Button(main_frame, text='자막 이미지 폴더 선택',
                   command=lambda: self.select_folder('subtitle')).grid(row=2, column=0, pady=5, sticky=tk.W)
        self.subtitle_label = ttk.Label(main_frame, text='자막 이미지 폴더: 선택되지 않음')
        self.subtitle_label.grid(row=3, column=0, pady=5, sticky=tk.W)

        ttk.Button(main_frame, text='음성 파일 폴더 선택',
                   command=lambda: self.select_folder('audio')).grid(row=4, column=0, pady=5, sticky=tk.W)
        self.audio_label = ttk.Label(main_frame, text='음성 파일 폴더: 선택되지 않음')
        self.audio_label.grid(row=5, column=0, pady=5, sticky=tk.W)

        # 사이드 영상 선택 버튼 추가
        ttk.Button(main_frame, text='사이드 영상 선택',
                   command=self.select_side_video).grid(row=6, column=0, pady=5, sticky=tk.W)
        self.side_video_label = ttk.Label(main_frame, text='사이드 영상: 선택되지 않음')
        self.side_video_label.grid(row=7, column=0, pady=5, sticky=tk.W)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, length=400, mode='determinate',
                                            variable=self.progress_var)
        self.progress_bar.grid(row=8, column=0, pady=10, sticky=tk.W + tk.E)

        self.status_label = ttk.Label(main_frame, text='대기 중...')
        self.status_label.grid(row=9, column=0, pady=5, sticky=tk.W)

        ttk.Button(main_frame, text='영상 제작',
                   command=self.start_video_creation).grid(row=10, column=0, pady=10, sticky=tk.W)

    def select_side_video(self):
        """사이드 영상 선택"""
        file_path = filedialog.askopenfilename(
            title='사이드 영상 선택',
            filetypes=[('Video files', '*.mp4 *.avi *.mov')]
        )
        if file_path:
            self.side_video_path = file_path
            self.side_video_label.config(text=f'사이드 영상: {file_path}')

    def select_folder(self, folder_type):
        folder = filedialog.askdirectory(title='폴더 선택')
        if folder:
            if folder_type == 'main':
                self.main_img_path = folder
                self.main_img_label.config(text=f'메인 이미지 폴더: {folder}')
            elif folder_type == 'subtitle':
                self.subtitle_path = folder
                self.subtitle_label.config(text=f'자막 이미지 폴더: {folder}')
            else:
                self.audio_path = folder
                self.audio_label.config(text=f'음성 파일 폴더: {folder}')

    def get_wav_duration(self, wav_path):
        with wave.open(wav_path, 'rb') as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            duration = frames / float(rate)
            return duration

    def load_and_resize_image(self, image_path, target_size):
        """PIL을 사용하여 이미지 로드 및 리사이즈"""
        try:
            with Image.open(image_path) as img:
                if img.mode == 'RGBA':
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3])
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')

                img.thumbnail(target_size, Image.Resampling.LANCZOS)
                new_img = Image.new('RGB', target_size, (255, 255, 255))
                paste_x = (target_size[0] - img.size[0]) // 2
                paste_y = (target_size[1] - img.size[1]) // 2
                new_img.paste(img, (paste_x, paste_y))

                return cv2.cvtColor(np.array(new_img), cv2.COLOR_RGB2BGR)
        except Exception as e:
            print(f"이미지 로드 중 오류 발생: {str(e)} - {image_path}")
            raise

    def create_frame(self, main_img_path, subtitle_img_path, side_frame, frame_size):
        """단일 프레임 생성 (사이드 영상 포함)"""
        try:
            # 메인 영상과 사이드 영상의 크기 설정
            main_width = 1370
            side_width = 550
            height = 1080

            # 메인 이미지 로드 및 리사이즈
            main_img = self.load_and_resize_image(main_img_path, (main_width, height))

            # 최종 프레임 생성 (1920x1080)
            final_frame = np.zeros((height, main_width + side_width, 3), dtype=np.uint8)

            # 메인 이미지를 왼쪽에 배치
            final_frame[:, :main_width] = main_img

            # 사이드 영상 프레임을 오른쪽에 배치
            if side_frame is not None:
                resized_side = cv2.resize(side_frame, (side_width, height))
                final_frame[:, main_width:] = resized_side

            # PIL을 사용하여 자막 이미지 로드
            with Image.open(subtitle_img_path) as subtitle_pil:
                # 고정 자막 높이 설정
                target_height = 90

                # 원본 크기에서 너비/높이 비율 계산
                aspect_ratio = subtitle_pil.size[0] / subtitle_pil.size[1]

                # 원하는 높이에 맞춘 너비 계산 (메인 영상 너비에 맞춤)
                target_width = int(target_height * aspect_ratio)

                # 만약 계산된 너비가 메인 영상 너비보다 크다면 비율을 유지하며 축소
                if target_width > main_width:
                    target_width = main_width
                    target_height = int(target_width / aspect_ratio)

                if subtitle_pil.mode == 'RGBA':
                    subtitle_pil = subtitle_pil.resize((target_width, target_height), Image.Resampling.LANCZOS)
                    subtitle = np.array(subtitle_pil)

                    # 알파 채널 분리
                    alpha = subtitle[:, :, 3] / 255.0
                    # RGB to BGR 변환
                    bgr = cv2.cvtColor(subtitle[:, :, :3], cv2.COLOR_RGB2BGR)

                    # 자막 위치 계산 (메인 영상 하단 중앙)
                    y_pos = height - target_height - 60
                    x_pos = (main_width - target_width) // 2

                    # 자막 영역 추출
                    roi = final_frame[y_pos:y_pos + target_height, x_pos:x_pos + target_width]

                    # 알파 블렌딩
                    for c in range(3):
                        roi[:, :, c] = roi[:, :, c] * (1 - alpha) + bgr[:, :, c] * alpha

                    # 블렌딩된 영역을 다시 메인 이미지에 삽입
                    final_frame[y_pos:y_pos + target_height, x_pos:x_pos + target_width] = roi
                else:
                    subtitle_pil = subtitle_pil.convert('RGB')
                    subtitle_pil = subtitle_pil.resize((target_width, target_height), Image.Resampling.LANCZOS)
                    subtitle = cv2.cvtColor(np.array(subtitle_pil), cv2.COLOR_RGB2BGR)

                    y_pos = height - target_height - 60
                    x_pos = (main_width - target_width) // 2
                    final_frame[y_pos:y_pos + target_height, x_pos:x_pos + target_width] = subtitle

            return final_frame

        except Exception as e:
            print(f"프레임 생성 중 오류 발생: {str(e)}")
            raise

    def create_video(self, save_path):
        try:
            main_images = sorted(
                [f for f in os.listdir(self.main_img_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
            subtitle_images = sorted(
                [f for f in os.listdir(self.subtitle_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
            audio_files = sorted([f for f in os.listdir(self.audio_path) if f.lower().endswith('.wav')])

            # 프레임 크기를 1920x1080으로 설정
            frame_size = (1920, 1080)
            fps = 24

            # 사이드 영상 로드
            side_video = None
            side_frame = None
            if self.side_video_path:
                side_video = cv2.VideoCapture(self.side_video_path)

            temp_video_path = f'temp_video_{datetime.now().strftime("%Y%m%d_%H%M%S")}.mp4'
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(temp_video_path, fourcc, fps, frame_size)

            total_files = len(main_images)
            total_frames = 0

            # 총 프레임 수 계산
            for audio_file in audio_files:
                audio_path = os.path.join(self.audio_path, audio_file)
                duration = self.get_wav_duration(audio_path)
                total_frames += int(duration * fps)

            frame_count = 0
            for i in range(total_files):
                progress = int((i / total_files) * 100)
                self.root.after(0, self.update_progress, progress, f'처리 중... {i + 1}/{total_files}')

                main_img_path = os.path.join(self.main_img_path, main_images[i])
                subtitle_img_path = os.path.join(self.subtitle_path, subtitle_images[i])
                audio_path = os.path.join(self.audio_path, audio_files[i])

                duration = self.get_wav_duration(audio_path)
                section_frame_count = int(duration * fps)

                for _ in range(section_frame_count):
                    # 사이드 영상 프레임 읽기
                    if side_video is not None:
                        ret, side_frame = side_video.read()
                        if not ret:  # 사이드 영상이 끝났으면 검은 화면으로
                            side_frame = np.zeros((1080, 550, 3), dtype=np.uint8)

                    frame = self.create_frame(main_img_path, subtitle_img_path, side_frame, frame_size)
                    out.write(frame)
                    frame_count += 1

            if side_video is not None:
                side_video.release()
            out.release()

            self.root.after(0, self.update_progress, 95, '오디오 병합 중...')
            audio_inputs = []
            filter_complex = []

            for i, audio_file in enumerate(audio_files):
                audio_inputs.extend(['-i', os.path.join(self.audio_path, audio_file)])
                filter_complex.append(f'[{i + 1}:a]')

            filter_complex = ''.join(filter_complex) + f'concat=n={len(audio_files)}:v=0:a=1[aout]'

            # ffmpeg 명령어 구성
            ffmpeg_command = ['ffmpeg', '-y', '-i', temp_video_path] + audio_inputs + \
                             ['-filter_complex', filter_complex, '-map', '0:v', '-map', '[aout]',
                              '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',  # 비디오 코덱 설정 추가
                              '-c:a', 'aac', '-b:a', '192k',  # 오디오 코덱 설정 추가
                              save_path]

            import subprocess
            subprocess.run(ffmpeg_command)

            os.remove(temp_video_path)

            self.root.after(0, self.update_progress, 100, '완료!')
            messagebox.showinfo('완료', '영상 제작이 완료되었습니다!')

        except Exception as e:
            self.root.after(0, self.update_progress, 0, '오류 발생')
            messagebox.showerror('오류', f'영상 제작 중 오류가 발생했습니다:\n{str(e)}')
            raise


    def start_video_creation(self):
        if not all([self.main_img_path, self.subtitle_path, self.audio_path]):
            messagebox.showwarning('경고', '필수 폴더를 모두 선택해주세요!')
            return

        save_path = filedialog.asksaveasfilename(
            defaultextension='.mp4',
            filetypes=[('MP4 files', '*.mp4')],
            title='영상 저장'
        )

        if save_path:
            thread = threading.Thread(target=self.create_video, args=(save_path,))
            thread.daemon = True
            thread.start()


    def update_progress(self, value, message):
        self.progress_var.set(value)
        self.status_label.config(text=message)
        self.root.update_idletasks()


if __name__ == '__main__':
    root = tk.Tk()
    app = VideoMakerApp(root)
    root.mainloop()