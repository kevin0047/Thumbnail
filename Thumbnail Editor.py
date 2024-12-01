import tkinter as tk
from tkinter import filedialog, colorchooser, messagebox, scrolledtext
from PIL import Image, ImageTk, ImageFont, ImageDraw
import cv2
import numpy as np
import os


class ThumbnailEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("썸네일 편집기")

        # 이미지 관련 변수
        self.image = None
        self.photo = None
        self.current_text = ""
        self.text_position = (50, 50)
        self.text_color = "#FFFFFF"
        self.text_size = 48
        self.display_scale = 1.0
        self.line_spacing = 1.2  # 줄간격 비율 추가

        # 폰트 경로 설정
        self.font_path = "Recipekorea 레코체 FONT.ttf"
        if not os.path.exists(self.font_path):
            messagebox.showwarning("폰트 경고", f"'{self.font_path}' 폰트 파일을 찾을 수 없습니다. 기본 폰트를 사용합니다.")

        self.setup_ui()

    def get_font(self, size):
        try:
            return ImageFont.truetype(self.font_path, size)
        except Exception as e:
            print(f"폰트 로드 실패: {e}")
            try:
                return ImageFont.truetype("malgun.ttf", size)
            except:
                return ImageFont.load_default()

    def setup_ui(self):
        # 버튼 프레임
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10)

        tk.Button(button_frame, text="이미지 열기", command=self.load_image).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="텍스트 색상", command=self.choose_color).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="저장하기", command=self.save_image).pack(side=tk.LEFT, padx=5)

        # 텍스트 입력 (Text 위젯으로 변경)
        text_frame = tk.Frame(self.root)
        text_frame.pack(pady=5)
        tk.Label(text_frame, text="텍스트:").pack(side=tk.LEFT)
        self.text_entry = scrolledtext.ScrolledText(text_frame, width=50, height=4)
        self.text_entry.pack(side=tk.LEFT, padx=5)
        tk.Button(text_frame, text="텍스트 적용", command=self.update_text).pack(side=tk.LEFT, padx=5)

        # 설정 프레임
        settings_frame = tk.Frame(self.root)
        settings_frame.pack(pady=5)

        # 폰트 크기 조절
        size_frame = tk.Frame(settings_frame)
        size_frame.pack(side=tk.LEFT, padx=10)
        tk.Label(size_frame, text="폰트 크기:").pack(side=tk.LEFT)
        self.size_scale = tk.Scale(size_frame, from_=12, to=100, orient=tk.HORIZONTAL,
                                   command=lambda x: self.update_font_size(int(x)))
        self.size_scale.set(48)
        self.size_scale.pack(side=tk.LEFT, padx=5)

        # 줄간격 조절
        spacing_frame = tk.Frame(settings_frame)
        spacing_frame.pack(side=tk.LEFT, padx=10)
        tk.Label(spacing_frame, text="줄간격:").pack(side=tk.LEFT)
        self.spacing_scale = tk.Scale(spacing_frame, from_=1.0, to=3.0, resolution=0.1,
                                      orient=tk.HORIZONTAL, command=self.update_line_spacing)
        self.spacing_scale.set(1.2)
        self.spacing_scale.pack(side=tk.LEFT, padx=5)

        # 이미지 표시 영역
        self.canvas = tk.Canvas(self.root, width=800, height=600, bg='gray')
        self.canvas.pack(pady=10)
        self.canvas.bind('<Button-1>', self.on_canvas_click)

    def draw_multiline_text(self, draw, position, text, font, fill):
        lines = text.split('\n')
        x, y = position
        line_height = font.getbbox('A')[3] * self.line_spacing  # 줄 높이 계산

        for line in lines:
            draw.text((x, y), line, font=font, fill=fill)
            y += line_height  # 다음 줄로 이동

    def update_canvas(self):
        if self.image is not None:
            try:
                canvas_width = self.canvas.winfo_width()
                canvas_height = self.canvas.winfo_height()

                img_width, img_height = self.image.size

                width_ratio = canvas_width / img_width
                height_ratio = canvas_height / img_height
                self.display_scale = min(width_ratio, height_ratio)

                new_width = int(img_width * self.display_scale)
                new_height = int(img_height * self.display_scale)

                display_image = self.image.copy()
                display_image = display_image.resize((new_width, new_height), Image.LANCZOS)

                draw = ImageDraw.Draw(display_image)
                font = self.get_font(self.text_size)

                # 멀티라인 텍스트 그리기
                self.draw_multiline_text(draw, self.text_position, self.current_text,
                                         font, self.text_color)

                self.photo = ImageTk.PhotoImage(display_image)
                self.canvas.delete("all")
                self.canvas.create_image(canvas_width // 2, canvas_height // 2,
                                         image=self.photo, anchor=tk.CENTER)

            except Exception as e:
                messagebox.showerror("Error", f"이미지 업데이트 중 오류가 발생했습니다:\n{str(e)}")

    def update_text(self):
        self.current_text = self.text_entry.get('1.0', 'end-1c')  # Text 위젯에서 텍스트 가져오기
        self.update_canvas()

    def update_line_spacing(self, value):
        self.line_spacing = float(value)
        self.update_canvas()

    # 나머지 메소드들은 이전과 동일...aa
    def load_image(self):
        try:
            file_path = filedialog.askopenfilename(filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.bmp *.gif *.tiff")])

            if file_path and os.path.exists(file_path):
                self.image = Image.open(file_path)
                self.update_canvas()
            else:
                if file_path:
                    messagebox.showerror("Error", "선택한 파일을 찾을 수 없습니다.")
        except Exception as e:
            messagebox.showerror("Error", f"이미지를 불러오는 중 오류가 발생했습니다:\n{str(e)}")

    def on_canvas_click(self, event):
        if self.image is not None:
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()

            img_width, img_height = self.image.size
            new_width = int(img_width * self.display_scale)
            new_height = int(img_height * self.display_scale)

            img_x = (canvas_width - new_width) // 2
            img_y = (canvas_height - new_height) // 2

            self.text_position = (event.x - img_x, event.y - img_y)
            self.update_canvas()

    def choose_color(self):
        color = colorchooser.askcolor(title="텍스트 색상 선택")
        if color[1]:
            self.text_color = color[1]
            self.update_canvas()

    def update_font_size(self, value):
        self.text_size = value
        self.update_canvas()

    def save_image(self):
        if self.image is not None:
            try:
                file_path = filedialog.asksaveasfilename(
                    defaultextension=".png",
                    filetypes=[("PNG files", "*.png"),
                               ("JPEG files", "*.jpg"),
                               ("All files", "*.*")]
                )

                if file_path:
                    save_image = self.image.copy()
                    draw = ImageDraw.Draw(save_image)

                    font = self.get_font(int(self.text_size / self.display_scale))

                    orig_x = int(self.text_position[0] / self.display_scale)
                    orig_y = int(self.text_position[1] / self.display_scale)

                    self.draw_multiline_text(draw, (orig_x, orig_y),
                                             self.current_text, font, self.text_color)

                    save_image.save(file_path)
                    messagebox.showinfo("성공", "이미지가 성공적으로 저장되었습니다!")

            except Exception as e:
                messagebox.showerror("Error", f"이미지 저장 중 오류가 발생했습니다:\n{str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    app = ThumbnailEditor(root)
    root.mainloop()