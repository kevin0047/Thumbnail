import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import cv2
import numpy as np
from PIL import Image, ImageFilter, ImageSequence
import threading
import wave
from datetime import datetime
import subprocess


class VideoMakerApp:
    def __init__(self, root):
        self.root = root
        self.root.title('영상 제작 프로그램')
        self.root.geometry('1000x800')

        self.side_video_path = r'C:\Users\ska00\Desktop\news\output_comments.mp4'
        self.items = []  # 이미지/영상, 자막, 음성 파일 정보를 저장할 리스트
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
    def get_media_duration(self, file_path):
        """미디어 파일(비디오/오디오)의 길이를 반환"""
        if file_path.lower().endswith('.wav'):
            with wave.open(file_path, 'rb') as wav_file:
                frames = wav_file.getnframes()
                rate = wav_file.getframerate()
                return frames / float(rate)
        elif file_path.lower().endswith(('.mp4', '.avi', '.mov', '.gif')):
            cap = cv2.VideoCapture(file_path)
            if cap.isOpened():
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                duration = frame_count / fps
                cap.release()
                return duration
            return 0
        return 0

    def process_video_frame(self, frame, target_size):
        """비디오 프레임 처리"""
        if frame is None:
            return np.zeros((target_size[1], target_size[0], 3), dtype=np.uint8)

        # 원본 크기 유지하면서 최대 크기에 맞추기
        height, width = frame.shape[:2]
        max_width, max_height = 1370, 1080

        # 스케일 계산
        scale = min(max_width / width, max_height / height)
        if scale < 1:  # 이미지가 더 큰 경우만 축소
            new_width = int(width * scale)
            new_height = int(height * scale)
            frame = cv2.resize(frame, (new_width, new_height))

        # 블러 배경 생성
        background = cv2.resize(frame, (target_size[0], target_size[1]))
        background = cv2.GaussianBlur(background, (99, 99), 30)

        # 프레임을 중앙에 배치
        height, width = frame.shape[:2]
        y_offset = (target_size[1] - height) // 2
        x_offset = (target_size[0] - width) // 2

        background[y_offset:y_offset + height, x_offset:x_offset + width] = frame
        return background

    def calculate_panning_parameters(self, image_path, target_size):
        """이미지의 패닝 파라미터 계산"""
        img = Image.open(image_path)
        img_width, img_height = img.size
        target_width, target_height = target_size

        # 이미지를 화면에 꽉 차게 리사이징
        img_ratio = img_width / img_height
        target_ratio = target_width / target_height

        if img_ratio > target_ratio:
            # 세로에 맞추고 가로는 잘림
            new_height = target_height
            new_width = int(new_height * img_ratio)
            return {
                'direction': 'horizontal',
                'size': (new_width, new_height),
                'total_move': new_width - target_width
            }
        else:
            # 가로에 맞추고 세로는 잘림
            new_width = target_width
            new_height = int(new_width / img_ratio)
            return {
                'direction': 'vertical',
                'size': (new_width, new_height),
                'total_move': new_height - target_height
            }

    def apply_panning(self, img, params, progress, target_size):
        """패닝 효과 적용"""
        if params['direction'] == 'horizontal':
            # 좌에서 우로 이동
            offset = int(params['total_move'] * progress)
            x_offset = -offset
            y_offset = 0
        else:
            # 위에서 아래로 이동
            offset = int(params['total_move'] * progress)
            x_offset = 0
            y_offset = -offset

        # 새 캔버스 생성
        canvas = np.zeros((target_size[1], target_size[0], 3), dtype=np.uint8)

        # 이미지 위치 계산
        x_start = max(0, x_offset)
        y_start = max(0, y_offset)
        x_end = min(target_size[0], x_offset + params['size'][0])
        y_end = min(target_size[1], y_offset + params['size'][1])

        img_x_start = max(0, -x_offset)
        img_y_start = max(0, -y_offset)
        img_x_end = img_x_start + (x_end - x_start)
        img_y_end = img_y_start + (y_end - y_start)

        canvas[y_start:y_end, x_start:x_end] = img[img_y_start:img_y_end, img_x_start:img_x_end]
        return canvas
    def create_frame(self, main_path, subtitle_img_path, side_frame, frame_size, frame_index, total_frames, panning_enabled=False):
        """프레임 생성 함수 수정"""
        main_width = 1370
        side_width = 550
        height = 1080

        # 메인 컨텐츠 처리 (이미지 또는 비디오)
        if main_path.lower().endswith(('.mp4', '.avi', '.mov', '.gif')):
            cap = cv2.VideoCapture(main_path)
            # 프레임 인덱스에 따라 적절한 프레임 추출
            total_video_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if total_video_frames > 0:
                target_frame = frame_index % total_video_frames
                cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
                ret, main_frame = cap.read()
                cap.release()
                if ret:
                    main_img = self.process_video_frame(main_frame, (main_width, height))
                else:
                    main_img = np.zeros((height, main_width, 3), dtype=np.uint8)
            else:
                main_img = np.zeros((height, main_width, 3), dtype=np.uint8)
        else:
            if panning_enabled:
                # 패닝 효과 적용
                img = cv2.imread(main_path)
                if img is None:
                    main_img = np.zeros((height, main_width, 3), dtype=np.uint8)
                else:
                    params = self.calculate_panning_parameters(main_path, (main_width, height))
                    img = cv2.resize(img, params['size'])
                    progress = frame_index / total_frames
                    main_img = self.apply_panning(img, params, progress, (main_width, height))
            else:
                # 기존 이미지 처리 방식
                main_img = self.process_image(main_path, (main_width, height), 'original')

        # 최종 프레임 생성
        final_frame = np.zeros((height, main_width + side_width, 3), dtype=np.uint8)
        final_frame[:, :main_width] = main_img

        # 사이드 영상 프레임 배치
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

            # 각 클립의 시작 시간과 길이를 저장할 리스트
            clip_start_times = []
            clip_durations = []
            current_time = 0

            # 각 클립의 길이 계산
            for item in self.items:
                main_path = item[0]
                audio_path = item[2]

                # 비디오/GIF와 오디오 중 더 긴 길이 사용
                video_duration = self.get_media_duration(main_path)
                audio_duration = self.get_media_duration(audio_path)
                clip_duration = max(video_duration, audio_duration)

                clip_start_times.append(current_time)
                clip_durations.append(clip_duration)
                current_time += clip_duration

            total_frames = int(current_time * fps)
            frame_count = 0

            # 프레임 생성 및 저장
            for frame_idx in range(total_frames):
                current_time = frame_idx / fps

                # 현재 프레임이 속한 클립 찾기
                current_clip_idx = 0
                for i in range(len(clip_start_times)):
                    if current_time >= clip_start_times[i]:
                        current_clip_idx = i
                    else:
                        break

                item = self.items[current_clip_idx]
                if side_video is not None:
                    ret, side_frame = side_video.read()
                    if not ret:
                        side_frame = np.zeros((1080, 550, 3), dtype=np.uint8)

                # 현재 클립 내에서의 프레임 인덱스 계산
                clip_frame_idx = frame_idx - int(clip_start_times[current_clip_idx] * fps)
                clip_total_frames = int(clip_durations[current_clip_idx] * fps)

                frame = self.create_frame(
                    item[0],  # main_path
                    item[1],  # subtitle_path
                    side_frame,
                    frame_size,
                    clip_frame_idx,
                    clip_total_frames,
                    item[4] if len(item) > 4 else False  # 패닝 효과 활성화 여부
                )
                out.write(frame)
                frame_count += 1

                progress = int((frame_count / total_frames) * 95)
                self.root.after(0, self.update_progress, progress, f'처리 중... {frame_count}/{total_frames}')

            if side_video is not None:
                side_video.release()
            out.release()

            self.root.after(0, self.update_progress, 95, '오디오 병합 중...')

            # ffmpeg 명령어 생성
            ffmpeg_inputs = ['-i', temp_video_path]
            filter_complex = []
            input_index = 1

            # 각 클립의 오디오 처리
            for i, item in enumerate(self.items):
                main_path = item[0]
                audio_path = item[2]

                # 메인 비디오의 오디오가 있는 경우
                if main_path.lower().endswith(('.mp4', '.avi', '.mov')):
                    ffmpeg_inputs.extend(['-i', main_path])
                    filter_complex.append(
                        f'[{input_index}:a]adelay={int(clip_start_times[i] * 1000)}|{int(clip_start_times[i] * 1000)}[v{i}];')
                    input_index += 1

                # 음성 클립 추가
                ffmpeg_inputs.extend(['-i', audio_path])
                filter_complex.append(
                    f'[{input_index}:a]adelay={int(clip_start_times[i] * 1000)}|{int(clip_start_times[i] * 1000)}[a{i}];')
                input_index += 1

            # 모든 오디오 트랙 믹스
            mix_inputs = []
            for i in range(len(self.items)):
                if self.items[i][0].lower().endswith(('.mp4', '.avi', '.mov')):
                    mix_inputs.append(f'[v{i}]')
                mix_inputs.append(f'[a{i}]')

            filter_complex.append(f'{"".join(mix_inputs)}amix=inputs={len(mix_inputs)}:duration=longest[aout]')

            # 최종 ffmpeg 명령어 실행
            ffmpeg_command = ['ffmpeg', '-y'] + ffmpeg_inputs + \
                             ['-filter_complex', ''.join(filter_complex),
                              '-map', '0:v', '-map', '[aout]',
                              '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
                              '-c:a', 'aac', '-b:a', '192k',
                              save_path]

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
        self.geometry('800x450')
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
        # 이미지 패닝 효과 옵션 추가
        self.panning_enabled = tk.BooleanVar(value=False)
        self.panning_frame = ttk.LabelFrame(main_frame, text="이미지 패닝 효과", padding="5")
        self.panning_frame.grid(row=4, column=0, columnspan=3, pady=10, sticky='ew')

        self.panning_check = ttk.Checkbutton(self.panning_frame, text="자동 패닝 효과 적용",
                                             variable=self.panning_enabled)
        self.panning_check.pack(side='left', padx=20)
        # 버튼 프레임
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=3, pady=10)

        ttk.Button(button_frame, text="확인", command=self.confirm, width=10).pack(side='left', padx=10)
        ttk.Button(button_frame, text="취소", command=self.cancel, width=10).pack(side='left', padx=10)

    def browse_file(self, file_type):
        filetypes = []
        if file_type == 'main':
            filetypes = [
                ('All supported files', '*.png *.jpg *.jpeg *.mp4 *.avi *.mov *.gif'),
                ('Image files', '*.png *.jpg *.jpeg'),
                ('Video files', '*.mp4 *.avi *.mov *.gif')
            ]
        elif file_type == 'subtitle':
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
            self.display_mode.get(),
            self.panning_enabled.get()  # 패닝 효과 상태 추가
        )
        self.destroy()

    def cancel(self):
        self.destroy()


if __name__ == '__main__':
    root = tk.Tk()
    app = VideoMakerApp(root)
    root.mainloop()