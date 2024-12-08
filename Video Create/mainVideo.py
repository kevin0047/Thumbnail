import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import cv2
import numpy as np
from PIL import Image, ImageFilter
import threading
import wave
from datetime import datetime


class VideoMakerApp:
    def __init__(self, root):
        self.root = root
        self.root.title('영상 제작 프로그램')
        self.root.geometry('1000x800')

        self.side_video_path = r'C:\Users\ska00\Desktop\news\output_comments.mp4'
        self.items = []  # 이미지, 자막, 음성 파일 정보를 저장할 리스트
        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 사이드 영상 선택 버튼
        ttk.Button(main_frame, text='사이드 영상 선택',
                   command=self.select_side_video).grid(row=0, column=0, pady=5, sticky=tk.W)
        self.side_video_label = ttk.Label(main_frame, text='사이드 영상: 선택되지 않음')
        self.side_video_label.grid(row=1, column=0, pady=5, sticky=tk.W)

        # 리스트 관리 위젯
        list_frame = ttk.LabelFrame(main_frame, text="이미지 및 음성 관리", padding="5")
        list_frame.grid(row=2, column=0, columnspan=2, sticky='nsew', pady=10)

        # 컨트롤 버튼
        control_frame = ttk.Frame(list_frame)
        control_frame.pack(fill='x', pady=5)
        ttk.Button(control_frame, text="항목 추가", command=self.add_item).pack(side='left', padx=5)
        ttk.Button(control_frame, text="선택 항목 삭제", command=self.delete_selected).pack(side='left', padx=5)

        # 트리뷰 생성
        self.tree = ttk.Treeview(list_frame, columns=('Main', 'Subtitle', 'Audio', 'Display'), show='headings',
                                 height=10)
        self.tree.heading('Main', text='메인 이미지')
        self.tree.heading('Subtitle', text='자막 이미지')
        self.tree.heading('Audio', text='음성 파일')
        self.tree.heading('Display', text='표시 방식')

        # 컬럼 너비 설정
        self.tree.column('Main', width=250)
        self.tree.column('Subtitle', width=250)
        self.tree.column('Audio', width=250)
        self.tree.column('Display', width=100)

        self.tree.pack(fill='both', expand=True)

        # 스크롤바
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.tree.yview)
        scrollbar.pack(side='right', fill='y')
        self.tree.configure(yscrollcommand=scrollbar.set)

        # 진행바 및 상태 표시
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, length=400, mode='determinate',
                                            variable=self.progress_var)
        self.progress_bar.grid(row=3, column=0, pady=10, sticky=tk.W + tk.E)

        self.status_label = ttk.Label(main_frame, text='대기 중...')
        self.status_label.grid(row=4, column=0, pady=5, sticky=tk.W)

        # 영상 제작 버튼
        ttk.Button(main_frame, text='영상 제작',
                   command=self.start_video_creation).grid(row=5, column=0, pady=10, sticky=tk.W)

    def select_side_video(self):
        file_path = filedialog.askopenfilename(
            title='사이드 영상 선택',
            filetypes=[('Video files', '*.mp4 *.avi *.mov')]
        )
        if file_path:
            self.side_video_path = file_path
            self.side_video_label.config(text=f'사이드 영상: {file_path}')

    def add_item(self):
        dialog = ItemDialog(self.root)
        self.root.wait_window(dialog)
        if dialog.result:
            self.tree.insert('', 'end', values=dialog.result)
            self.items.append(dialog.result)

    def delete_selected(self):
        selected = self.tree.selection()
        for item in selected:
            self.tree.delete(item)
            index = self.tree.index(item)
            if 0 <= index < len(self.items):
                self.items.pop(index)

    def process_image(self, image_path, target_size, display_mode='fit'):
        """이미지 처리 함수"""
        img = Image.open(image_path)

        if display_mode == 'fit':
            # 화면에 맞춤 모드 (비율 유지하며 화면 가득 채움)
            img_ratio = img.size[0] / img.size[1]
            target_ratio = target_size[0] / target_size[1]

            if img_ratio > target_ratio:
                new_height = target_size[1]
                new_width = int(new_height * img_ratio)
            else:
                new_width = target_size[0]
                new_height = int(new_width / img_ratio)

            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        else:  # 원본 크기 모드
            # 원본 이미지가 target_size보다 큰 경우 축소
            scale = 1.0
            if img.size[0] > target_size[0] or img.size[1] > target_size[1]:
                # 가로세로 비율 유지하면서 화면 안에 들어오도록 축소
                width_scale = target_size[0] / img.size[0]
                height_scale = target_size[1] / img.size[1]
                scale = min(width_scale, height_scale) * 0.95  # 여유 공간을 위해 95%로 축소

                new_width = int(img.size[0] * scale)
                new_height = int(img.size[1] * scale)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # 블러 처리된 배경 생성
            background = img.copy()
            background = background.resize(target_size, Image.Resampling.LANCZOS)
            background = background.filter(ImageFilter.GaussianBlur(radius=30))

            # 조정된 원본 이미지를 중앙에 배치
            paste_x = (target_size[0] - img.size[0]) // 2
            paste_y = (target_size[1] - img.size[1]) // 2
            background.paste(img, (paste_x, paste_y))
            img = background

        # PIL Image를 OpenCV 형식으로 변환
        if img.mode == 'RGBA':
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    def get_wav_duration(self, wav_path):
        with wave.open(wav_path, 'rb') as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            duration = frames / float(rate)
            return duration

    def create_frame(self, main_img_path, subtitle_img_path, side_frame, frame_size, display_mode):
        try:
            # 메인 영상과 사이드 영상의 크기 설정
            main_width = 1370
            side_width = 550
            height = 1080

            # 메인 이미지 처리
            main_img = self.process_image(main_img_path, (main_width, height), display_mode)

            # 최종 프레임 생성
            final_frame = np.zeros((height, main_width + side_width, 3), dtype=np.uint8)

            # 메인 이미지를 왼쪽에 배치
            if display_mode == 'fit':
                # 이미지가 프레임보다 큰 경우 중앙 부분을 사용
                if main_img.shape[1] > main_width:
                    start = (main_img.shape[1] - main_width) // 2
                    main_img = main_img[:, start:start + main_width]
                if main_img.shape[0] > height:
                    start = (main_img.shape[0] - height) // 2
                    main_img = main_img[start:start + height]

            # 이미지 크기가 타겟 크기와 다른 경우 리사이즈
            main_img = cv2.resize(main_img, (main_width, height))
            final_frame[:, :main_width] = main_img

            # 사이드 영상 프레임을 오른쪽에 배치
            if side_frame is not None:
                resized_side = cv2.resize(side_frame, (side_width, height))
                final_frame[:, main_width:] = resized_side

            # 자막 처리
            subtitle_img = Image.open(subtitle_img_path)
            target_height = 90
            aspect_ratio = subtitle_img.size[0] / subtitle_img.size[1]
            target_width = int(target_height * aspect_ratio)

            if target_width > main_width:
                target_width = main_width
                target_height = int(target_width / aspect_ratio)

            subtitle_img = subtitle_img.resize((target_width, target_height), Image.Resampling.LANCZOS)

            if subtitle_img.mode == 'RGBA':
                subtitle = np.array(subtitle_img)
                alpha = subtitle[:, :, 3] / 255.0
                bgr = cv2.cvtColor(subtitle[:, :, :3], cv2.COLOR_RGB2BGR)

                y_pos = height - target_height - 60
                x_pos = (main_width - target_width) // 2
                roi = final_frame[y_pos:y_pos + target_height, x_pos:x_pos + target_width]

                for c in range(3):
                    roi[:, :, c] = roi[:, :, c] * (1 - alpha) + bgr[:, :, c] * alpha

                final_frame[y_pos:y_pos + target_height, x_pos:x_pos + target_width] = roi
            else:
                subtitle_img = subtitle_img.convert('RGB')
                subtitle = cv2.cvtColor(np.array(subtitle_img), cv2.COLOR_RGB2BGR)
                y_pos = height - target_height - 60
                x_pos = (main_width - target_width) // 2
                final_frame[y_pos:y_pos + target_height, x_pos:x_pos + target_width] = subtitle

            return final_frame

        except Exception as e:
            print(f"프레임 생성 중 오류 발생: {str(e)}")
            raise

    def create_video(self, save_path):
        try:
            if not self.items:
                raise ValueError("추가된 항목이 없습니다.")

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

            total_items = len(self.items)
            total_frames = 0

            # 총 프레임 수 계산
            for item in self.items:
                audio_path = item[2]  # 음성 파일 경로
                duration = self.get_wav_duration(audio_path)
                total_frames += int(duration * fps)

            frame_count = 0
            for i, item in enumerate(self.items):
                progress = int((i / total_items) * 100)
                self.root.after(0, self.update_progress, progress, f'처리 중... {i + 1}/{total_items}')

                main_img_path = item[0]  # 메인 이미지 경로
                subtitle_img_path = item[1]  # 자막 이미지 경로
                audio_path = item[2]  # 음성 파일 경로
                display_mode = item[3]  # 표시 방식

                duration = self.get_wav_duration(audio_path)
                section_frame_count = int(duration * fps)

                for _ in range(section_frame_count):
                    if side_video is not None:
                        ret, side_frame = side_video.read()
                        if not ret:
                            side_frame = np.zeros((1080, 550, 3), dtype=np.uint8)

                    frame = self.create_frame(main_img_path, subtitle_img_path, side_frame, frame_size, display_mode)
                    out.write(frame)
                    frame_count += 1

            if side_video is not None:
                side_video.release()
            out.release()

            self.root.after(0, self.update_progress, 95, '오디오 병합 중...')

            # 오디오 처리
            audio_inputs = []
            filter_complex = []

            for i, item in enumerate(self.items):
                audio_inputs.extend(['-i', item[2]])  # 음성 파일 경로
                filter_complex.append(f'[{i + 1}:a]')

            filter_complex = ''.join(filter_complex) + f'concat=n={len(self.items)}:v=0:a=1[aout]'

            ffmpeg_command = ['ffmpeg', '-y', '-i', temp_video_path] + audio_inputs + \
                             ['-filter_complex', filter_complex, '-map', '0:v', '-map', '[aout]',
                              '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
                              '-c:a', 'aac', '-b:a', '192k',
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
        if not self.items:
            messagebox.showwarning('경고', '추가된 항목이 없습니다!')
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


class ItemDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("항목 추가")
        self.result = None
        self.create_widgets()

        # 모달 창으로 설정
        self.transient(parent)
        self.grab_set()

        # 창 크기와 위치 설정
        self.geometry('500x250')
        self.resizable(False, False)

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill='both', expand=True)

        # 메인 이미지 선택
        ttk.Label(main_frame, text="메인 이미지:").grid(row=0, column=0, padx=5, pady=5, sticky='e')
        self.main_path = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.main_path, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(main_frame, text="찾아보기", command=lambda: self.browse_file('main')).grid(row=0, column=2, padx=5)

        # 자막 이미지 선택
        ttk.Label(main_frame, text="자막 이미지:").grid(row=1, column=0, padx=5, pady=5, sticky='e')
        self.subtitle_path = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.subtitle_path, width=50).grid(row=1, column=1, padx=5)
        ttk.Button(main_frame, text="찾아보기", command=lambda: self.browse_file('subtitle')).grid(row=1, column=2, padx=5)

        # 음성 파일 선택
        ttk.Label(main_frame, text="음성 파일:").grid(row=2, column=0, padx=5, pady=5, sticky='e')
        self.audio_path = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.audio_path, width=50).grid(row=2, column=1, padx=5)
        ttk.Button(main_frame, text="찾아보기", command=lambda: self.browse_file('audio')).grid(row=2, column=2, padx=5)

        # 이미지 표시 방식 선택
        display_frame = ttk.LabelFrame(main_frame, text="이미지 표시 방식", padding="5")
        display_frame.grid(row=3, column=0, columnspan=3, pady=10, sticky='ew')

        self.display_mode = tk.StringVar(value="fit")
        ttk.Radiobutton(display_frame, text="화면에 맞춤 (비율 유지, 잘림 허용)",
                        variable=self.display_mode, value="fit").pack(side='left', padx=20)
        ttk.Radiobutton(display_frame, text="원본 크기 (블러 배경)",
                        variable=self.display_mode, value="original").pack(side='left', padx=20)

        # 버튼 프레임
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=3, pady=10)

        ttk.Button(button_frame, text="확인", command=self.confirm, width=10).pack(side='left', padx=10)
        ttk.Button(button_frame, text="취소", command=self.cancel, width=10).pack(side='left', padx=10)

    def browse_file(self, file_type):
        filetypes = []
        if file_type in ['main', 'subtitle']:
            filetypes = [('Image files', '*.png *.jpg *.jpeg')]
        elif file_type == 'audio':
            filetypes = [('Audio files', '*.wav')]

        path = filedialog.askopenfilename(filetypes=filetypes)
        if path:
            if file_type == 'main':
                self.main_path.set(path)
            elif file_type == 'subtitle':
                self.subtitle_path.set(path)
            else:
                self.audio_path.set(path)

    def confirm(self):
        # 모든 필드가 채워졌는지 확인
        if not all([self.main_path.get(), self.subtitle_path.get(), self.audio_path.get()]):
            messagebox.showwarning('경고', '모든 파일을 선택해주세요!')
            return

        self.result = (
            self.main_path.get(),
            self.subtitle_path.get(),
            self.audio_path.get(),
            self.display_mode.get()
        )
        self.destroy()

    def cancel(self):
        self.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    app = VideoMakerApp(root)
    root.mainloop()