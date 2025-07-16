import streamlit as st
import io
import docx
import fitz  # PyMuPDF
import openai
from openai import OpenAI
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate
from reportlab.lib.units import mm
import tempfile

# --- Cấu hình và Thiết lập ---
st.set_page_config(page_title="Trích xuất Thông tin Thông minh", page_icon="✨", layout="wide")

# --- API Key cho Groq ---
try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except (KeyError, FileNotFoundError):
    st.warning("Không tìm thấy Groq API Key trong Streamlit secrets. Vui lòng nhập thủ công để chạy ứng dụng.")
    GROQ_API_KEY = st.text_input("Nhập Groq API Key của bạn:", type="password")
    if not GROQ_API_KEY:
        st.info("Vui lòng cung cấp API key để bắt đầu.")
        st.stop()

# Khởi tạo client tương thích Groq
client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

# --- Hàm gọi Groq API ---
def get_groq_response(input_text, prompt, model="llama3-8b-8192"):
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Bạn là một trợ lý AI thông minh, chuyên trích xuất thông tin từ tài liệu."},
                {"role": "user", "content": input_text},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Đã xảy ra lỗi khi gọi Groq API: {e}"

# --- Hàm xử lý file ---
def extract_text_from_docx(docx_bytes):
    try:
        doc = docx.Document(io.BytesIO(docx_bytes))
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    full_text.append(cell.text)
        return '\n'.join(full_text)
    except Exception as e:
        st.error(f"Lỗi đọc file .docx: {e}")
        return None

def extract_text_from_pdf(file_bytes):
    try:
        pdf_document = fitz.open(stream=file_bytes, filetype="pdf")
        full_text = ""
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            full_text += page.get_text()
        pdf_document.close()
        return full_text
    except Exception as e:
        st.error(f"Lỗi đọc file .pdf: {e}")
        return None

# --- Hàm tạo PDF từ kết quả ---
def export_to_pdf(text_output):
    """
    Tạo file PDF từ text_output bằng phong cách bố cục đẹp như LaTeX.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        file_path = tmp_file.name

    doc = SimpleDocTemplate(file_path, pagesize=A4,
                            rightMargin=20, leftMargin=20,
                            topMargin=20, bottomMargin=20)

    styles = getSampleStyleSheet()
    styleN = styles["Normal"]
    styleH = styles["Heading1"]

    elements = []

    # Tiêu đề
    elements.append(Paragraph("Thông tin trích xuất từ tài liệu", styleH))
    elements.append(Paragraph("<br/>", styleN))

    # Xử lý từng dòng kết quả
    for line in text_output.strip().split("\n"):
        if line.strip() != "":
            line = line.replace("**", "")  # loại bỏ markdown nếu có
            elements.append(Paragraph(line, styleN))

    doc.build(elements)
    return file_path

# --- Giao diện Streamlit ---
st.title("✨ Trích xuất Thông tin từ Tài liệu với Groq AI")
st.markdown("Tải lên tệp `.docx` hoặc `.pdf` để bắt đầu.")

col1, col2 = st.columns([2, 3])

with col1:
    st.header("1. Tải lên & Tùy chỉnh")

    uploaded_file = st.file_uploader("Chọn một tệp (.docx hoặc .pdf)", type=['docx', 'pdf'])

    prompt_default = """Bạn là một trợ lý AI chuyên nghiệp trong việc trích xuất thông tin.

Từ nội dung đề cương học phần dưới đây, hãy trích xuất và trình bày rõ ràng theo kiểu đánh số thứ tự theo các mục sau:
1. Tên học phần
2. Mã học phần (nếu có)
3. Số tín chỉ
4. Điều kiện tiên quyết (nếu có)
5. Mục tiêu học phần
6. Chuẩn đầu ra của học phần (CLO)
7. Nội dung học phần tóm tắt
8. Tài liệu tham khảo (ghi rõ tên, tác giả, năm, NXB nếu có)

Nếu không tìm thấy thông tin nào, hãy ghi là "Không tìm thấy".
"""
    prompt_user = st.text_area("Chỉnh sửa prompt:", value=prompt_default, height=350)
    submit_button = st.button("🚀 Bắt đầu trích xuất")

with col2:
    st.header("2. Kết quả trích xuất")
    result_container = st.container()
    result_container.info("Kết quả sẽ được hiển thị ở đây sau khi bạn nhấn nút 'Bắt đầu trích xuất'.")

    if submit_button:
        if uploaded_file and prompt_user:
            with st.spinner("Đang xử lý file... Vui lòng chờ! 🤖"):
                file_bytes = uploaded_file.getvalue()
                file_extension = uploaded_file.name.split('.')[-1].lower()
                raw_text = None

                st.info(f"Đang đọc file {file_extension}...")
                if file_extension == "docx":
                    raw_text = extract_text_from_docx(file_bytes)
                elif file_extension == "pdf":
                    raw_text = extract_text_from_pdf(file_bytes)

                if raw_text and raw_text.strip():
                    st.success("Đọc file thành công!")
                    st.info("Đang gửi nội dung đến mô hình AI...")
                    response = get_groq_response(raw_text, prompt_user)
                    result_container.text_area("Thông tin đã trích xuất:", value=response, height=550)

                    # Nút để xuất PDF
                    if response and st.button("📄 Xuất ra file PDF"):
                        with st.spinner("Đang tạo file PDF..."):
                            pdf_file_path = export_to_pdf(response)
                            with open(pdf_file_path, "rb") as f:
                                st.download_button(
                                    label="📥 Tải về PDF",
                                    data=f,
                                    file_name="thong_tin_trich_xuat.pdf",
                                    mime="application/pdf"
                                )
                elif raw_text is not None:
                    result_container.warning("Không tìm thấy nội dung văn bản nào trong file.")
                else:
                    result_container.error("Lỗi khi trích xuất nội dung. Vui lòng thử lại với file khác.")
        elif not uploaded_file:
            st.warning("Vui lòng tải lên một file.")
        else:
            st.warning("Prompt không được để trống.")
