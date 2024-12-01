import tkinter as tk
from tkinter import filedialog, colorchooser, messagebox, scrolledtext
from PIL import Image, ImageTk, ImageFont, ImageDraw
import cv2
import numpy as np
import os
import re


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
        self.line_spacing = 1.2

        # 그림자 효과 변수
        self.shadow_enabled = tk.BooleanVar(value=False)
        self.shadow_color = "#000000"
        self.shadow_offset = 3

        # 폰트 경로 설정
        self.font_path = "Recipekorea 레코체 FONT.ttf"
        if not os.path.exists(self.font_path):
            messagebox.showwarning("폰트 경고", f"'{self.font_path}' 폰트 파일을 찾을 수 없습니다.")

        self.setup_ui()

        # 색상 하이라이트를 위한 정규식 패턴
        self.color_pattern = re.compile(r'<([^>]+)>([^<]+)</>')

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
        # 메인 프레임
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 왼쪽 패널 (설정)
        left_panel = tk.Frame(main_frame)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=5)

        # 버튼들
        tk.Button(left_panel, text="이미지 열기", command=self.load_image).pack(fill=tk.X, pady=2)
        tk.Button(left_panel, text="기본 텍스트 색상", command=self.choose_color).pack(fill=tk.X, pady=2)

        # 그림자 설정
        shadow_frame = tk.LabelFrame(left_panel, text="그림자 설정")
        shadow_frame.pack(fill=tk.X, pady=5)

        tk.Checkbutton(shadow_frame, text="그림자 효과", variable=self.shadow_enabled,
                       command=self.update_canvas).pack(anchor=tk.W)

        tk.Button(shadow_frame, text="그림자 색상",
                  command=self.choose_shadow_color).pack(fill=tk.X, pady=2)

        tk.Label(shadow_frame, text="그림자 거리:").pack(anchor=tk.W)
        self.shadow_scale = tk.Scale(shadow_frame, from_=1, to=10, orient=tk.HORIZONTAL,
                                     command=self.update_shadow_offset)
        self.shadow_scale.set(3)
        self.shadow_scale.pack(fill=tk.X)

        # 폰트 크기
        font_frame = tk.LabelFrame(left_panel, text="폰트 설정")
        font_frame.pack(fill=tk.X, pady=5)

        tk.Label(font_frame, text="크기:").pack(anchor=tk.W)
        self.size_scale = tk.Scale(font_frame, from_=12, to=100, orient=tk.HORIZONTAL,
                                   command=self.update_font_size)
        self.size_scale.set(48)
        self.size_scale.pack(fill=tk.X)

        tk.Label(font_frame, text="줄간격:").pack(anchor=tk.W)
        self.spacing_scale = tk.Scale(font_frame, from_=1.0, to=3.0, resolution=0.1,
                                      orient=tk.HORIZONTAL, command=self.update_line_spacing)
        self.spacing_scale.set(1.2)
        self.spacing_scale.pack(fill=tk.X)

        # 오른쪽 패널
        right_panel = tk.Frame(main_frame)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        # 텍스트 입력 영역
        text_frame = tk.LabelFrame(right_panel, text="텍스트 입력")
        text_frame.pack(fill=tk.X, pady=5)

        help_text = "색상 적용 방법: <#색상코드>텍스트</>\n예시: <#FF0000>빨간색</> 텍스트"
        tk.Label(text_frame, text=help_text, justify=tk.LEFT).pack(anchor=tk.W)

        self.text_entry = scrolledtext.ScrolledText(text_frame, width=50, height=4)
        self.text_entry.pack(pady=5)
        tk.Button(text_frame, text="텍스트 적용", command=self.update_text).pack()

        # 이미지 미리보기
        preview_frame = tk.LabelFrame(right_panel, text="미리보기")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.canvas = tk.Canvas(preview_frame, width=800, height=600, bg='gray')
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind('<Button-1>', self.on_canvas_click)

        # 저장 버튼
        tk.Button(right_panel, text="저장하기", command=self.save_image).pack(pady=5)

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

    def draw_text_with_effects(self, draw, position, text, font, default_color):
        x, y = position
        line_height = font.getbbox('A')[3] * self.line_spacing

        for line in text.split('\n'):
            current_x = x

            # 텍스트 파싱
            segments = []
            last_end = 0
            for match in self.color_pattern.finditer(line):
                if match.start() > last_end:
                    segments.append((line[last_end:match.start()], default_color))
                segments.append((match.group(2), match.group(1)))
                last_end = match.end()
            if last_end < len(line):
                segments.append((line[last_end:], default_color))

            if not segments:
                segments = [(line, default_color)]

            for text_segment, color in segments:
                if self.shadow_enabled.get():
                    draw.text((current_x + self.shadow_offset, y + self.shadow_offset),
                              text_segment, font=font, fill=self.shadow_color)

                draw.text((current_x, y), text_segment, font=font, fill=color)
                bbox = draw.textlength(text_segment, font=font)
                current_x += bbox

            y += line_height

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

                self.draw_text_with_effects(draw, self.text_position,
                                            self.current_text, font, self.text_color)

                self.photo = ImageTk.PhotoImage(display_image)
                self.canvas.delete("all")
                self.canvas.create_image(canvas_width // 2, canvas_height // 2,
                                         image=self.photo, anchor=tk.CENTER)

            except Exception as e:
                messagebox.showerror("Error", f"이미지 업데이트 중 오류가 발생했습니다:\n{str(e)}")

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

    def update_text(self):
        self.current_text = self.text_entry.get('1.0', 'end-1c')
        self.update_canvas()

    def choose_color(self):
        color = colorchooser.askcolor(title="텍스트 색상 선택", color=self.text_color)
        if color[1]:
            self.text_color = color[1]
            self.update_canvas()

    def choose_shadow_color(self):
        color = colorchooser.askcolor(title="그림자 색상 선택", color=self.shadow_color)
        if color[1]:
            self.shadow_color = color[1]
            self.update_canvas()

    def update_shadow_offset(self, value):
        self.shadow_offset = int(value)
        self.update_canvas()

    def update_font_size(self, value):
        self.text_size = int(value)
        self.update_canvas()

    def update_line_spacing(self, value):
        self.line_spacing = float(value)
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

                    self.draw_text_with_effects(draw, (orig_x, orig_y),
                                                self.current_text, font, self.text_color)

                    save_image.save(file_path)
                    messagebox.showinfo("성공", "이미지가 성공적으로 저장되었습니다!")

            except Exception as e:
                messagebox.showerror("Error", f"이미지 저장 중 오류가 발생했습니다:\n{str(e)}")


def main():
    root = tk.Tk()
    app = ThumbnailEditor(root)
    root.mainloop()


if __name__ == "__main__":
    main()