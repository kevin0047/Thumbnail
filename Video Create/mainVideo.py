import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageSequence, ImageFilter, ImageDraw
import cv2
import numpy as np
import os
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import multiprocessing
from queue import Queue
import threading
import gc


class ImageCompositor:
    def __init__(self, root):
        self.root = root
        self.root.title("이미지 합성 프로그램")
        self.root.geometry("800x700")

        # 멀티프로세싱/스레딩 설정
        self.num_cpu_cores = multiprocessing.cpu_count()
        self.thread_pool = ThreadPoolExecutor(max_workers=self.num_cpu_cores)
        self.process_pool = ProcessPoolExecutor(max_workers=self.num_cpu_cores - 1)
        self.frame_queue = Queue(maxsize=30)

        # CUDA 지원 확인
        self.use_cuda = cv2.cuda.getCudaEnabledDeviceCount() > 0
        if self.use_cuda:
            self.gpu_stream = cv2.cuda.Stream()
            print("CUDA GPU 가속 활성화됨")
        else:
            print("CUDA GPU 미지원, CPU 모드로 실행")

        # 변수 초기화
        self.background_image = None
        self.background_frames = []
        self.background_pil = None
        self.original_background = None
        self.is_gif = False
        self.current_frame = 0
        self.object_images = []
        self.preview_photo = None
        self.canvas_width = 480
        self.canvas_height = 320
        self.output_width = 1370
        self.output_height = 1080
        self.selected_object = None
        self.dragging = False
        self.duration = tk.StringVar(value="3")
        self.aspect_ratio_var = tk.StringVar(value="fit")
        self.background_options = {
            "fit": "화면 맞춤",
            "fill": "가득 채우기"
        }
        self.motion_type = tk.StringVar(value="none")
        self.motion_options = {
            "none": "모션 없음",
            "left": "왼쪽으로 이동",
            "right": "오른쪽으로 이동",
            "up": "위로 이동",
            "down": "아래로 이동",
            "zoom_in": "줌인",
            "zoom_out": "줌아웃"
        }
        self.motion_scale = tk.StringVar(value="1.2")

        # 메모리 캐시
        self.image_cache = {}
        self.max_cache_size = 100  # MB

        self.create_widgets()
        self.bind_events()

    def create_widgets(self):
        # 스크롤바를 포함할 컨테이너 프레임
        container = ttk.Frame(self.root)
        container.pack(expand=True, fill='both', padx=10, pady=10)

        # 수직 스크롤바
        scrollbar = ttk.Scrollbar(container, orient="vertical")
        scrollbar.pack(side="right", fill="y")

        # 스크롤 캔버스
        scroll_canvas = tk.Canvas(container, yscrollcommand=scrollbar.set)
        scroll_canvas.pack(side="left", fill="both", expand=True)

        scrollbar.config(command=scroll_canvas.yview)

        # 메인 프레임
        self.main_frame = ttk.Frame(scroll_canvas)
        scroll_canvas.create_window((0, 0), window=self.main_frame, anchor="nw")

        # 미리보기 캔버스
        self.canvas = tk.Canvas(self.main_frame, bg='black',
                                width=self.canvas_width, height=self.canvas_height)
        self.canvas.pack(pady=10)

        # 배경 이미지 옵션 프레임
        bg_option_frame = ttk.LabelFrame(self.main_frame, text="배경 이미지 옵션")
        bg_option_frame.pack(fill='x', pady=5, padx=5)

        for value, text in self.background_options.items():
            ttk.Radiobutton(bg_option_frame, text=text, value=value,
                            variable=self.aspect_ratio_var,
                            command=self.load_background).pack(side='left', padx=5)

        # 컨트롤 프레임
        control_frame = ttk.Frame(self.main_frame)
        control_frame.pack(fill='x', pady=5)

        ttk.Button(control_frame, text="배경 이미지 선택",
                   command=self.load_background).pack(side='left', padx=5)
        self.object_btn = ttk.Button(control_frame, text="객체 이미지 추가",
                                     command=self.load_object, state='disabled')
        self.object_btn.pack(side='left', padx=5)

        # 객체 조작 프레임
        object_control_frame = ttk.LabelFrame(self.main_frame, text="객체 조작")
        object_control_frame.pack(fill='x', pady=5, padx=5)

        ttk.Label(object_control_frame, text="크기 조절:").pack(side='left', padx=5)
        self.scale_slider = ttk.Scale(object_control_frame, from_=0.1, to=2.0,
                                      orient='horizontal', command=self.scale_object)
        self.scale_slider.set(1.0)
        self.scale_slider.pack(side='left', padx=5, fill='x', expand=True)

        self.delete_btn = ttk.Button(object_control_frame, text="선택 객체 삭제",
                                     command=self.delete_object, state='disabled')
        self.delete_btn.pack(side='right', padx=5)

        # 모션 설정 프레임
        motion_frame = ttk.LabelFrame(self.main_frame, text="배경 모션 설정")
        motion_frame.pack(fill='x', pady=5, padx=5)

        ttk.Label(motion_frame, text="모션 효과:").pack(side='left', padx=5)
        motion_combo = ttk.Combobox(motion_frame,
                                    textvariable=self.motion_type,
                                    values=list(self.motion_options.keys()),
                                    state='readonly',
                                    width=15)
        motion_combo.pack(side='left', padx=5)

        ttk.Label(motion_frame, text="모션 크기(배율):").pack(side='left', padx=5)
        ttk.Entry(motion_frame, textvariable=self.motion_scale, width=5).pack(side='left', padx=5)

        # 영상 설정 프레임
        video_frame = ttk.LabelFrame(self.main_frame, text="영상 설정")
        video_frame.pack(fill='x', pady=5, padx=5)

        ttk.Label(video_frame, text="영상 길이(초):").pack(side='left', padx=5)
        ttk.Entry(video_frame, textvariable=self.duration, width=5).pack(side='left', padx=5)

        self.create_btn = ttk.Button(video_frame, text="영상 생성",
                                     command=self.create_video, state='disabled')
        self.create_btn.pack(side='right', padx=5)

        # 객체 목록
        self.object_list = ttk.Treeview(self.main_frame,
                                        columns=("순서", "테두리"),
                                        height=5)
        self.object_list.heading("#0", text="객체")
        self.object_list.heading("순서", text="순서")
        self.object_list.heading("테두리", text="테두리")
        self.object_list.pack(fill='x', pady=5, padx=5)

        # 스크롤 영역 업데이트
        self.main_frame.bind("<Configure>",
                             lambda e: scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all")))

    def bind_events(self):
        self.canvas.bind("<Button-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.bind("<ButtonRelease-1>", self.stop_drag)
        self.object_list.bind("<<TreeviewSelect>>", self.select_object_from_list)

    def load_background(self):
        file_path = filedialog.askopenfilename(
            title="배경 이미지 선택",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp")]
        )

        if not file_path:
            return

        try:
            self.original_background = Image.open(file_path)

            if file_path.lower().endswith('.gif'):
                self.is_gif = True
                self.background_frames = []
                for frame in ImageSequence.Iterator(self.original_background):
                    frame = frame.convert('RGBA')
                    new_width, new_height = self.calculate_background_size(frame)
                    frame = frame.resize((new_width, new_height),
                                         Image.Resampling.LANCZOS)
                    self.background_frames.append(ImageTk.PhotoImage(frame))
                self.background_image = self.background_frames[0]
                self.animate_gif()
            else:
                self.is_gif = False
                self.background_pil = self.original_background.convert('RGBA')
                new_width, new_height = self.calculate_background_size(self.background_pil)
                self.background_pil = self.background_pil.resize(
                    (new_width, new_height), Image.Resampling.LANCZOS)
                self.background_image = ImageTk.PhotoImage(self.background_pil)

            self.object_btn.config(state='normal')
            self.create_btn.config(state='normal')
            self.update_canvas()

        except Exception as e:
            messagebox.showerror("오류", f"이미지 로드 중 오류 발생: {str(e)}")

    def load_object(self):
        file_path = filedialog.askopenfilename(
            title="객체 이미지 선택",
            filetypes=[("PNG files", "*.png")]
        )

        if not file_path:
            return

        try:
            # 테두리 추가 여부를 묻는 다이얼로그
            add_border = messagebox.askyesno(
                "테두리 설정",
                "객체에 빨간색 테두리를 추가하시겠습니까?"
            )

            with Image.open(file_path) as image:
                image = image.convert('RGBA')

                if add_border:
                    # 테두리가 있는 새 이미지 생성
                    border_width = 2
                    new_size = (image.width + border_width * 2, image.height + border_width * 2)
                    bordered_image = Image.new('RGBA', new_size, (0, 0, 0, 0))

                    # 빨간색 테두리 그리기
                    for i in range(border_width):
                        # 테두리용 마스크 생성
                        mask = Image.new('RGBA', new_size, (0, 0, 0, 0))
                        draw = ImageDraw.Draw(mask)
                        draw.rectangle(
                            [i, i, new_size[0] - i - 1, new_size[1] - i - 1],
                            outline=(255, 0, 0, 255)
                        )
                        bordered_image = Image.alpha_composite(bordered_image, mask)

                    # 원본 이미지를 테두리 안에 붙이기
                    bordered_image.paste(image, (border_width, border_width), image)
                    image = bordered_image

                # 객체 크기 최적화
                max_width = self.canvas_width // 4
                max_height = self.canvas_height // 4

                ratio = min(max_width / image.width, max_height / image.height)
                new_width = int(image.width * ratio)
                new_height = int(image.height * ratio)

                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(image)

                # 중앙 배치
                pos = (self.canvas_width // 2, self.canvas_height // 2)

                # add_border 정보도 함께 저장
                self.object_images.append((image, photo, pos, 1.0, add_border))

                self.update_canvas()
                self.update_object_list()

        except Exception as e:
            messagebox.showerror("오류", f"이미지 로드 중 오류 발생: {str(e)}")

    def calculate_background_size(self, image):
        img_width, img_height = image.size
        canvas_ratio = self.canvas_width / self.canvas_height
        img_ratio = img_width / img_height

        if self.aspect_ratio_var.get() == "fit":
            if img_ratio > canvas_ratio:
                new_width = self.canvas_width
                new_height = int(new_width / img_ratio)
            else:
                new_height = self.canvas_height
                new_width = int(new_height * img_ratio)
        else:  # "fill"
            if img_ratio > canvas_ratio:
                new_height = self.canvas_height
                new_width = int(new_height * img_ratio)
            else:
                new_width = self.canvas_width
                new_height = int(new_width / img_ratio)

        return new_width, new_height

    def create_blurred_background(self, image, canvas_size):
        background = Image.new('RGBA', (self.output_width, self.output_height))

        scale = 2.0
        blur_width = int(self.output_width * scale)
        blur_height = int(self.output_height * scale)

        img_ratio = image.width / image.height
        if img_ratio > 1:
            blur_width = int(blur_height * img_ratio)
        else:
            blur_height = int(blur_width / img_ratio)

        blurred = image.resize((blur_width, blur_height), Image.Resampling.LANCZOS)
        blurred = blurred.filter(ImageFilter.GaussianBlur(radius=30))

        x = (self.output_width - blur_width) // 2
        y = (self.output_height - blur_height) // 2
        background.paste(blurred, (x, y))

        return background.resize((self.output_width, self.output_height),
                                 Image.Resampling.LANCZOS)

    def update_canvas(self):
        self.canvas.delete("all")

        if self.background_image:
            if isinstance(self.background_image, ImageTk.PhotoImage):
                img_width = self.background_image.width()
                img_height = self.background_image.height()
            else:
                img_width = self.background_frames[0].width()
                img_height = self.background_frames[0].height()

            if self.aspect_ratio_var.get() == "fit" and \
                    (img_width < self.canvas_width or img_height < self.canvas_height):
                blurred_bg = self.create_blurred_background(
                    self.original_background,
                    (self.canvas_width, self.canvas_height)
                )
                self.blurred_photo = ImageTk.PhotoImage(blurred_bg)
                self.canvas.create_image(
                    self.canvas_width // 2,
                    self.canvas_height // 2,
                    image=self.blurred_photo,
                    anchor='center'
                )

            x = (self.canvas_width - img_width) // 2
            y = (self.canvas_height - img_height) // 2
            self.canvas.create_image(
                x + img_width // 2,
                y + img_height // 2,
                image=self.background_image,
                anchor='center'
            )

            # 객체 이미지들 그리기
            for i, (_, photo, (x, y), _, has_border) in enumerate(self.object_images):
                item = self.canvas.create_image(x, y, image=photo, anchor='center')
                if i == self.selected_object:
                    bbox = self.canvas.bbox(item)
                    self.canvas.create_rectangle(bbox, outline='red', width=2)

    def create_video(self):
        if not self.background_pil:
            messagebox.showerror("오류", "배경 이미지를 선택해주세요!")
            return

        try:
            duration = float(self.duration.get())
            motion_scale = float(self.motion_scale.get())
            if duration <= 0 or motion_scale <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("오류", "올바른 값을 입력해주세요!")
            return

        output_path = filedialog.asksaveasfilename(
            defaultextension=".mp4",
            filetypes=[("MP4 files", "*.mp4")]
        )

        if not output_path:
            return

        # 프로그레스 바 생성
        progress_window = tk.Toplevel(self.root)
        progress_window.title("영상 생성 중...")
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(
            progress_window,
            variable=progress_var,
            maximum=100,
            length=300
        )
        progress_bar.pack(pady=10)

        # 영상 생성 스레드 시작
        thread = threading.Thread(
            target=self._create_video_thread,
            args=(output_path, duration, motion_scale, progress_var, progress_window),
            daemon=True
        )
        thread.start()

    def _create_video_thread(self, output_path, duration, motion_scale, progress_var, progress_window):
        try:
            frames = int(duration * 30)  # 30fps
            batch_size = min(30, max(1, frames // self.num_cpu_cores))

            # 비디오 설정
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(
                output_path,
                fourcc,
                30,
                (self.output_width, self.output_height)
            )

            # 프레임 생성 및 처리
            frame_batches = []
            current_batch = []

            for frame in range(frames):
                # 프레임 생성
                composite = self.create_frame(frame, frames)
                frame_array = cv2.cvtColor(np.array(composite), cv2.COLOR_RGBA2BGR)
                current_batch.append(frame_array)

                if len(current_batch) == batch_size or frame == frames - 1:
                    frame_batches.append(current_batch)
                    current_batch = []

                # 프로그레스 바 업데이트
                progress = (frame + 1) / frames * 100
                self.root.after(1, lambda p=progress: progress_var.set(p))

            # 배치 단위로 병렬 처리
            with ThreadPoolExecutor(max_workers=self.num_cpu_cores) as executor:
                futures = []
                for batch in frame_batches:
                    future = executor.submit(self.process_frame_batch, batch)
                    futures.append(future)

                # 결과 수집 및 저장
                for future in futures:
                    processed_frames = future.result()
                    for frame in processed_frames:
                        out.write(frame)

            out.release()
            self.clear_cache()

            # 완료 메시지
            self.root.after(0, lambda: messagebox.showinfo("성공", "영상이 생성되었습니다!"))
            self.root.after(0, progress_window.destroy)

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror(
                "오류",
                f"영상 생성 중 오류가 발생했습니다: {str(e)}"
            ))
            self.root.after(0, progress_window.destroy)
            if 'out' in locals():
                out.release()

    def apply_motion(self, progress):
        """모션 효과 적용"""
        motion_type = self.motion_type.get()
        motion_scale = float(self.motion_scale.get())

        if self.aspect_ratio_var.get() == "fit":
            bg_width, bg_height = self.calculate_background_size(self.original_background)
        else:
            bg_width = self.output_width
            bg_height = self.output_height

        # 모션에 따른 크기 및 위치 계산
        if motion_type == "zoom_in":
            scale = 1 + (motion_scale - 1) * progress
            current_width = int(bg_width * scale)
            current_height = int(bg_height * scale)
            x = (self.output_width - current_width) // 2
            y = (self.output_height - current_height) // 2

            bg_resized = self.original_background.resize(
                (current_width, current_height),
                Image.Resampling.LANCZOS
            )

        elif motion_type == "zoom_out":
            scale = motion_scale - (motion_scale - 1) * progress
            current_width = int(bg_width * scale)
            current_height = int(bg_height * scale)
            x = (self.output_width - current_width) // 2
            y = (self.output_height - current_height) // 2

            bg_resized = self.original_background.resize(
                (current_width, current_height),
                Image.Resampling.LANCZOS
            )

        elif motion_type in ["left", "right"]:
            scale = motion_scale
            current_width = int(bg_width * scale)
            current_height = bg_height

            if motion_type == "left":
                x = int(-((current_width - self.output_width) * progress))
            else:
                x = int(-((current_width - self.output_width) * (1 - progress)))

            y = (self.output_height - current_height) // 2
            bg_resized = self.original_background.resize(
                (current_width, current_height),
                Image.Resampling.LANCZOS
            )

        elif motion_type in ["up", "down"]:
            scale = motion_scale
            current_width = bg_width
            current_height = int(bg_height * scale)

            x = (self.output_width - current_width) // 2
            if motion_type == "up":
                y = int(-((current_height - self.output_height) * progress))
            else:
                y = int(-((current_height - self.output_height) * (1 - progress)))

            bg_resized = self.original_background.resize(
                (current_width, current_height),
                Image.Resampling.LANCZOS
            )

        else:  # no motion
            x = (self.output_width - bg_width) // 2
            y = (self.output_height - bg_height) // 2
            bg_resized = self.original_background.resize(
                (bg_width, bg_height),
                Image.Resampling.LANCZOS
            )

        # 합성용 이미지 생성
        composite = Image.new('RGBA', (self.output_width, self.output_height), (0, 0, 0, 0))

        # 블러 배경 추가 (fit 모드일 때)
        if self.aspect_ratio_var.get() == "fit":
            blurred_bg = self.create_blurred_background(
                self.original_background,
                (self.output_width, self.output_height)
            )
            composite.paste(blurred_bg, (0, 0))

        composite.paste(bg_resized, (int(x), int(y)))
        return composite

    def create_frame(self, frame_index, total_frames):
        """단일 프레임 생성"""
        progress = frame_index / total_frames

        # 배경 처리
        composite = self.apply_motion(progress)

        # 객체 합성
        scale_x = self.output_width / self.canvas_width
        scale_y = self.output_height / self.canvas_height

        # 수정된 부분
        for img, _, (obj_x, obj_y), obj_scale, _ in self.object_images:
            new_width = int(img.width * obj_scale * scale_x)
            new_height = int(img.height * obj_scale * scale_y)
            obj_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            new_x = int(obj_x * scale_x)
            new_y = int(obj_y * scale_y)

            composite.paste(
                obj_resized,
                (new_x - new_width // 2, new_y - new_height // 2),
                obj_resized
            )

        return composite

    def process_frame_batch(self, frames):
        """프레임 배치 처리"""
        if self.use_cuda:
            return self._process_frame_batch_gpu(frames)
        return frames

    def _process_frame_batch_gpu(self, frames):
        """GPU를 사용한 프레임 배치 처리"""
        processed_frames = []

        for frame in frames:
            gpu_frame = cv2.cuda_GpuMat()
            gpu_frame.upload(frame)

            # GPU 처리
            if self.motion_type.get() in ["zoom_in", "zoom_out"]:
                processed = cv2.cuda.resize(
                    gpu_frame,
                    (self.output_width, self.output_height)
                )
            else:
                processed = gpu_frame

            # CPU로 다운로드
            processed_frames.append(processed.download())

        return processed_frames

    def start_drag(self, event):
        self.dragging = False
        x, y = event.x, event.y

        for i, (_, _, (obj_x, obj_y), _, _) in enumerate(self.object_images):
            if abs(x - obj_x) < 50 and abs(y - obj_y) < 50:
                self.selected_object = i
                self.dragging = True
                self.delete_btn.config(state='normal')
                self.scale_slider.set(self.object_images[i][3])
                self.object_list.selection_set(str(i))
                break

    def drag(self, event):
        if self.dragging and self.selected_object is not None:
            img, photo, _, scale, has_border = self.object_images[self.selected_object]
            self.object_images[self.selected_object] = (img, photo, (event.x, event.y), scale, has_border)
            self.update_canvas()

    def stop_drag(self, event):
        self.dragging = False

    def scale_object(self, value):
        if self.selected_object is not None:
            scale = float(value)
            img, _, pos, _, has_border = self.object_images[self.selected_object]

            new_width = int(img.width * scale)
            new_height = int(img.height * scale)
            resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(resized_img)

            self.object_images[self.selected_object] = (img, photo, pos, scale, has_border)
            self.update_canvas()

    def delete_object(self):
        if self.selected_object is not None:
            del self.object_images[self.selected_object]
            self.selected_object = None
            self.delete_btn.config(state='disabled')
            self.update_canvas()
            self.update_object_list()

    def select_object_from_list(self, event):
        selection = self.object_list.selection()
        if selection:
            self.selected_object = int(selection[0])
            self.delete_btn.config(state='normal')
            self.scale_slider.set(self.object_images[self.selected_object][3])

    def update_object_list(self):
        self.object_list.delete(*self.object_list.get_children())
        for i, (img, _, _, _, has_border) in enumerate(self.object_images):
            border_text = "테두리 있음" if has_border else "테두리 없음"
            self.object_list.insert("", "end", iid=str(i),
                                    text=f"객체 {i + 1}",
                                    values=(i + 1, border_text))
    def animate_gif(self):
        if self.is_gif and self.background_frames:
            self.current_frame = (self.current_frame + 1) % len(self.background_frames)
            self.background_image = self.background_frames[self.current_frame]
            self.update_canvas()
            self.root.after(100, self.animate_gif)

    def clear_cache(self):
        """메모리 캐시 정리"""
        self.image_cache.clear()
        gc.collect()

    def __del__(self):
        """리소스 정리"""
        self.thread_pool.shutdown()
        self.process_pool.shutdown()
        self.clear_cache()

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageCompositor(root)
    root.mainloop()