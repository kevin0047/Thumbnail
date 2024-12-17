import tkinter as tk
from tkinter import messagebox
import os
import shutil


class FolderCleanupApp:
    def __init__(self, root):
        self.root = root
        self.root.title("폴더 정리 프로그램")

        # 창 크기 설정
        self.root.geometry("400x300")

        # 폴더 경로 리스트 (실제 경로로 수정해주세요)
        self.folders_to_clean = [
            r"C:\Users\ska00\Desktop\news\img",
            r"C:\Users\ska00\Desktop\news\txt",
            r"C:\Users\ska00\Desktop\news\voice"
        ]

        # 새 파일 생성 경로 (실제 경로로 수정해주세요)
        self.new_file_path = r"C:\Users\ska00\Desktop\news\대본.txt"

        # GUI 요소 생성
        self.create_widgets()

    def create_widgets(self):
        # 설명 라벨
        tk.Label(
            self.root,
            text="다음 폴더들의 내용이 삭제됩니다:",
            pady=10
        ).pack()

        # 폴더 목록 표시
        folder_frame = tk.Frame(self.root)
        folder_frame.pack(pady=10)

        for folder in self.folders_to_clean:
            tk.Label(folder_frame, text=folder).pack()

        # 새 파일 경로 표시
        tk.Label(
            self.root,
            text="\n새로 생성될 파일 경로:",
            pady=10
        ).pack()

        tk.Label(
            self.root,
            text=self.new_file_path
        ).pack()

        # 실행 버튼
        tk.Button(
            self.root,
            text="작업 실행",
            command=self.confirm_operation,
            width=20,
            height=2
        ).pack(pady=20)

    def confirm_operation(self):
        # 확인 메시지 표시
        response = messagebox.askyesno(
            "확인",
            "정말로 작업을 실행하시겠습니까?\n\n" +
            "주의: 지정된 폴더의 모든 내용이 삭제됩니다!"
        )

        if response:
            self.execute_operation()

    def execute_operation(self):
        try:
            # 폴더 내용 삭제
            for folder in self.folders_to_clean:
                if os.path.exists(folder):
                    for filename in os.listdir(folder):
                        file_path = os.path.join(folder, filename)
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                        elif os.path.isdir(file_path):
                            shutil.rmtree(file_path)

            # 새 파일 생성
            os.makedirs(os.path.dirname(self.new_file_path), exist_ok=True)
            with open(self.new_file_path, 'w', encoding='utf-8') as f:
                f.write(" ")

            messagebox.showinfo("완료", "작업이 성공적으로 완료되었습니다!")

        except Exception as e:
            messagebox.showerror("오류", f"작업 중 오류가 발생했습니다:\n{str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    app = FolderCleanupApp(root)
    root.mainloop()