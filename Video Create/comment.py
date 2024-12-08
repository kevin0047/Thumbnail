import tkinter as tk
from tkinter import ttk, messagebox
import winsound
from selenium import webdriver
from selenium.webdriver.common.by import By
from PIL import Image, ImageDraw, ImageFont
import re
import os
from threading import Thread
from commentVideo import CommentVideoGenerator

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

        self.save_path = tk.StringVar(value="C:/Users/ska00/Desktop/news")
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

    def clean_and_process_text(self, content_path):
        output_path = content_path.replace('content.txt', 'recontent.txt')

        with open(content_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        filtered_lines = []
        i = 0
        while i < len(lines):
            current_line = lines[i].strip()

            if current_line.startswith('https://youtube.com'):
                while i < len(lines) and not lines[i].strip().endswith('youtube.com'):
                    i += 1
                i += 1
                continue

            if current_line.startswith('http'):
                if i + 3 < len(lines):

                    if lines[i + 3].strip()[0].isascii() and lines[i + 3].strip()[0].isalpha():
                        i += 4  # 해당 블록 전체 스킵
                        continue
                    else:
                        i += 1  # https 줄만 스킵
                        continue
                else:
                    i += 1  # https 줄만 스킵
                    continue

            if '[원본 보기]' in current_line:
                i += 1
                continue

            filtered_lines.append(lines[i])
            i += 1

        # 빈 줄과 숫자만 있는 줄 제거
        non_empty_lines = [line.strip() for line in filtered_lines if line.strip() and not line.strip().isdigit()]

        # 마침표 추가 및 텍스트 정제
        cleaned_lines = []
        for line in non_empty_lines:
            clean_line = line.strip() + '.'
            clean_line = clean_line.replace('ㅋ', '.').replace('ㅂㄷ', '부들') \
                .replace('ㄹㅈㄷ', '레전드').replace('ㄱㅊ', '괜찮') \
                .replace('ㄳ', '감사').replace('ㄱㅅ', '감사') \
                .replace('ㅇㅇ', '.').replace('ㅉㅉ', '쯧쯧') \
                .replace('ㄷ', '.').replace('ㄹㅇ', '레알') \
                .replace('ㅠ', '.').replace('ㅜ', '.') \
                .replace('jpg', '.').replace('png', '.') \
                .replace('JPG', '.').replace('TXT', '.') \
                .replace('txt', '.').replace('GIF', '.') \
                .replace('gif', '.').replace('|', '.') \
                .replace('-', '.').replace('❗', '.') \
                .replace('!', '.').replace('❓', '.') \
                .replace('♥', '.').replace('♡', '.') \
                .replace('✋', '.').replace('ㅅㅂ', '.') \
                .replace('ㅆㅂ', '.').replace('ㅂㅅ', '.') \
                .replace('ㅄ', '.').replace('ㅁㅌㅊ', '몇타치') \
                .replace('ㄱㅆㅅㅌㅊ', '개씹상타치').replace('ㅆㅅㅌㅊ', '씹상타치') \
                .replace('ㅅㅌㅊ', '상타치').replace('ㅈㄴ', '존나') \
                .replace('ㅇㅈㄹ', '이지랄').replace('ㅇㅈ', '인정') \
                .replace('ㅈ', '좃').replace('1돌', '일돌') \
                .replace('2돌', '이돌').replace('3돌', '삼돌') \
                .replace('4돌', '사돌').replace('5돌', '오돌') \
                .replace('6돌', '육돌').replace('4성', '사성') \
                .replace('5성', '오성').replace('ㄴㄴ', '노노') \
                .replace('관련게시물 : ', '.') .replace('[단독]', '.')\

            while '..' in clean_line:
                clean_line = clean_line.replace('..', '.')
            cleaned_lines.append(clean_line)

        # 결과 저장
        text = '\n'.join(cleaned_lines).rstrip('.')
        with open(output_path, 'w', encoding='utf-8') as file:
            file.write(text)
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
            filter_words = ["틱톡", "https", "실베", "kakao",".com","gall","store","MeritTV","도배","디시","디씨","갤러리","갤"]  # 원하는 필터 단어 추가
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
            content_path = f"{base_path}/txt/content.txt"

            with open(content_path, 'a', encoding='utf-8') as f:
                f.write(f"{title}\n{content}\n")

            # 정제된 텍스트 생성
            self.clean_and_process_text(content_path)

            with open(f"{base_path}/txt/comment.txt", 'w', encoding='utf-8') as f:
                for comment in comment_text:
                    f.write(comment)
            driver.quit()

            # 댓글 영상 생성
            self.update_status("댓글 영상 생성 중...")
            try:
                comment_file = f"{base_path}/txt/comment.txt"
                video_output = f"{base_path}/output_comments.mp4"
                generator = CommentVideoGenerator()

                with open(comment_file, 'r', encoding='utf-8') as f:
                    comments = f.readlines()

                for comment in comments:
                    if comment.strip():  # 빈 줄 제외
                        generator.add_comment(comment)

                generator.create_video(video_output)
                self.update_status("댓글 영상 생성 완료!")
            except Exception as e:
                self.update_status(f"댓글 영상 생성 실패: {str(e)}")



            self.progress['value'] = 100

            winsound.PlaySound("SystemExit", winsound.SND_ALIAS)
            self.update_status("작업 완료!")
            self.start_button.config(state="normal")

        except Exception as e:
            self.update_status(f"오류 발생: {str(e)}")
            self.start_button.config(state="normal")
            messagebox.showerror("오류", str(e))







if __name__ == "__main__":
    root = tk.Tk()
    app = DataCollectorGUI(root)
    root.mainloop()