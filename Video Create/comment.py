import tkinter as tk
from tkinter import ttk, messagebox
import winsound
from selenium import webdriver
from selenium.webdriver.common.by import By
from PIL import Image, ImageDraw, ImageFont
import re
import os
from threading import Thread


class DataCollectorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("자료수집기")
        self.root.geometry("600x500")

        # URL 입력
        url_frame = ttk.LabelFrame(root, text="URL 입력", padding="10")
        url_frame.pack(fill="x", padx=10, pady=5)

        self.url_entry = ttk.Entry(url_frame, width=50)
        self.url_entry.pack(side="left", padx=5)

        # 경로 설정
        path_frame = ttk.LabelFrame(root, text="저장 경로 설정", padding="10")
        path_frame.pack(fill="x", padx=10, pady=5)

        self.save_path = tk.StringVar(value="C:/Users/ska00/Desktop/뉴스")
        path_entry = ttk.Entry(path_frame, textvariable=self.save_path, width=50)
        path_entry.pack(side="left", padx=5)

        # 진행 상태
        status_frame = ttk.LabelFrame(root, text="진행 상태", padding="10")
        status_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.status_text = tk.Text(status_frame, height=10, width=50)
        self.status_text.pack(padx=5, pady=5)

        # 진행바
        self.progress = ttk.Progressbar(root, length=400, mode='determinate')
        self.progress.pack(pady=10)

        # 실행 버튼
        self.start_button = ttk.Button(root, text="수집 시작", command=self.start_collection)
        self.start_button.pack(pady=10)

    def update_status(self, message):
        self.status_text.insert(tk.END, f"{message}\n")
        self.status_text.see(tk.END)

    def start_collection(self):
        if not self.url_entry.get():
            messagebox.showerror("오류", "URL을 입력해주세요.")
            return

        self.start_button.config(state="disabled")
        self.progress['value'] = 0
        Thread(target=self.collect_data).start()

    def collect_data(self):
        try:
            self.update_status("브라우저 실행 중...")
            options = webdriver.ChromeOptions()
            driver = webdriver.Chrome(options=options)

            self.update_status("페이지 로딩 중...")
            driver.get(self.url_entry.get())
            self.progress['value'] = 20

            # 제목 추출
            title_ = driver.find_element(By.XPATH,
                                         '//*[@id="container"]/section/article[2]/div[1]/header/div/h3/span[2]')
            title = title_.text
            self.update_status(f"제목 추출: {title}")
            self.progress['value'] = 40

            # 내용 추출
            element = driver.find_element(By.XPATH, '//div[@class="write_div"]')
            content = re.sub("- dc official App|이미지 순서 ON|마우스 커서를 올리면|이미지 순서를 ON/OFF 할 수 있습니다.", "", element.text)
            content += '\n/**/'
            self.progress['value'] = 60

            # 댓글 추출 및 처리
            self.update_status("댓글 추출 중...")
            parent_elements = driver.find_elements(By.XPATH,
                                                   '//div[@class="clear cmt_txtbox"] | //div[@class="clear cmt_txtbox btn_reply_write_all"]')
            filter_words = ["틱톡", "https", "실베", "kakao",".com","gall","store","MeritTV","도배","디시","디씨"]  # 원하는 필터 단어 추가
            seen_comments = set()  # 중복 체크를 위한 세트
            is_first_comment = True
            comment_text = []
            for element in parent_elements:
                comments = element.find_elements(By.XPATH, './/p[@class="usertxt ub-word"]')
                for comment in comments:
                    clean_comment = re.sub("- dc App|파파 너글|착한말하기|1일차", "", comment.text)

                    if any(word in clean_comment for word in filter_words):
                        continue

                    if clean_comment in seen_comments:
                        continue

                    if is_first_comment and "clear cmt_txtbox" == element.get_attribute("class"):
                        is_first_comment = False
                        continue

                    if "clear cmt_txtbox" == element.get_attribute("class"):
                        clean_comment = "┗ " + clean_comment

                    clean_comment = clean_comment.replace('\n', ' ')
                    seen_comments.add(clean_comment)  # 이 줄이 추가됨
                    comment_text.append(clean_comment + "\n")
                    is_first_comment = False

            self.progress['value'] = 80

            # 파일 저장
            self.update_status("파일 저장 중...")
            base_path = self.save_path.get()

            # 텍스트 저장
            os.makedirs(f"{base_path}/txt", exist_ok=True)
            with open(f"{base_path}/txt/content.txt", 'a', encoding='utf-8') as f:
                f.write(f"{title}\n{content}\n")

            with open(f"{base_path}/txt/comment.txt", 'w', encoding='utf-8') as f:
                for comment in comment_text:
                    f.write(comment)

            # 이미지 생성
            self.create_comment_images(comment_text, base_path)

            self.progress['value'] = 100
            driver.quit()
            winsound.PlaySound("SystemExit", winsound.SND_ALIAS)
            self.update_status("작업 완료!")
            self.start_button.config(state="normal")

        except Exception as e:
            self.update_status(f"오류 발생: {str(e)}")
            self.start_button.config(state="normal")
            messagebox.showerror("오류", str(e))

    def create_comment_images(self, comments, base_path):
        def create_image_with_comments(comments, font_size, font_name, bg_color, text_color, output_path):
            font = ImageFont.truetype(font_name, font_size)
            image = Image.new('RGB', (1610, 900), bg_color)
            draw = ImageDraw.Draw(image)

            ascent, descent = font.getmetrics()
            line_height = ascent + descent

            y, x = 20, 20
            for comment in comments:
                draw.text((x, y), comment, font=font, fill=text_color)
                y += line_height

                if y > 880:
                    y = 20
                    x += font.getbbox(comment)[2] + 40

            image.save(output_path)

        self.update_status("이미지 생성 중...")
        font_path = 'C:/Windows/Fonts/NanumGothic.ttf'
        counter = 1

        for i in range(0, len(comments), 130):
            comment_set = comments[i:i + 130]
            while os.path.exists(f"{base_path}/a ({counter}).png"):
                counter += 1
            create_image_with_comments(
                comment_set, 20, font_path, 'white', 'black',
                f"{base_path}/a ({counter}).png"
            )
            counter += 1


if __name__ == "__main__":
    root = tk.Tk()
    app = DataCollectorGUI(root)
    root.mainloop()