import streamlit as st
import json
from datetime import datetime
import os

# Cố gắng import Google Drive API nếu có sẵn
try:
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    import io
    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    GOOGLE_DRIVE_AVAILABLE = False

# Cấu hình trang
st.set_page_config(
    page_title="Bảng hỏi Sức khỏe Tâm thần",
    page_icon="🏥",
    layout="wide"
)

# CSS tùy chỉnh
st.markdown("""
<style>
    .main {
        padding: 2rem;
    }
    .stButton>button {
        width: 100%;
        background-color: #4CAF50;
        color: white;
        padding: 0.5rem;
        font-size: 1.1rem;
    }
    .question-box {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    .progress-text {
        text-align: center;
        color: #666;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Khởi tạo session state
if 'current_question' not in st.session_state:
    st.session_state.current_question = 'A1'
if 'answers' not in st.session_state:
    st.session_state.answers = {}
if 'history' not in st.session_state:
    st.session_state.history = ['A1']
if 'completed' not in st.session_state:
    st.session_state.completed = False
if 'respondent_name' not in st.session_state:
    st.session_state.respondent_name = ""

def upload_to_google_drive(respondent_name, answers):
    """Tải dữ liệu vào Google Sheet 'SurveyResults'"""
    try:
        import gspread
        from oauth2client.service_account import ServiceAccountCredentials
        
        # Chuẩn bị dữ liệu một dòng
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        row_data = [timestamp, respondent_name]
        
        # Thêm tất cả câu trả lời vào một dòng
        for q_id in sorted(answers.keys()):
            answer = answers[q_id]
            q_config = SURVEY_CONFIG.get(q_id, {})
            
            # Format câu trả lời
            if isinstance(answer, list):
                answer_text = []
                for val in answer:
                    for label, v in q_config.get('opts', []):
                        if v == val:
                            answer_text.append(label)
                            break
                answer_str = '; '.join(answer_text)
            elif q_config.get('type') == 'radio' and 'opts' in q_config:
                answer_str = ""
                for label, v in q_config['opts']:
                    if v == answer:
                        answer_str = label
                        break
            else:
                answer_str = str(answer).replace('\n', ' ')
            
            row_data.append(answer_str)
        
        # Lưu vào local CSV file
        local_filename = f"survey_response_{respondent_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        csv_content = "Timestamp,Tên Người Trả Lời," + ",".join(sorted(answers.keys())) + "\n"
        csv_content += ",".join([f'"{str(v).replace(chr(34), chr(34)+chr(34))}"' for v in row_data]) + "\n"
        
        with open(local_filename, 'w', encoding='utf-8') as f:
            f.write(csv_content)
        
        # Thử upload lên Google Sheet nếu có credentials
        try:
            creds_dict = None
            
            # Cách 1: Lấy từ Streamlit Secrets (dành cho deployment)
            if "google_credentials" in st.secrets:
                creds_dict = st.secrets["google_credentials"]
            # Cách 2: Lấy từ file cục bộ (dành cho development)
            elif os.path.exists('credentials.json'):
                import json as json_module
                with open('credentials.json', 'r') as f:
                    creds_dict = json_module.load(f)
            
            if creds_dict and GOOGLE_DRIVE_AVAILABLE:
                # Sử dụng gspread để thêm dữ liệu vào Google Sheet
                try:
                    from gspread import service_account
                    
                    # Xác thực với Google Sheets
                    gc = service_account.Credentials.from_service_account_info(
                        creds_dict,
                        scopes=['https://www.googleapis.com/auth/spreadsheets', 
                                'https://www.googleapis.com/auth/drive']
                    )
                    
                    client = gspread.authorize(gc)
                    
                    # Mở Google Sheet có tên 'SurveyResults'
                    worksheet = client.open("SurveyResults").sheet1
                    
                    # Thêm dòng dữ liệu mới
                    worksheet.append_row(row_data)
                    
                    st.success(f"✅ Dữ liệu đã được lưu vào Google Sheet 'SurveyResults' thành công!")
                except gspread.exceptions.SpreadsheetNotFound:
                    st.warning("⚠️ Không tìm thấy Google Sheet 'SurveyResults'. Hãy kiểm tra lại tên sheet.")
                    st.info(f"✅ Dữ liệu đã được lưu vào file local: {local_filename}")
                except Exception as e:
                    st.warning(f"⚠️ Lỗi khi truy cập Google Sheet: {str(e)}")
                    st.info(f"✅ Dữ liệu đã được lưu vào file local: {local_filename}")
            else:
                st.success(f"✅ Dữ liệu đã được lưu thành công!")
                st.info(f"📁 File local: {local_filename}")
                st.info("💡 Để gửi dữ liệu vào Google Sheet, hãy cấu hình credentials")
        
        except ImportError:
            st.success(f"✅ Dữ liệu đã được lưu vào file local: {local_filename}")
            st.info("💡 Để gửi dữ liệu vào Google Sheet, cài đặt: `pip install gspread oauth2client`")
        
        return local_filename
    except Exception as e:
        st.error(f"❌ Lỗi khi lưu dữ liệu: {str(e)}")
        return None

def get_next_question_logic(current_q, answers):
    """Logic phân nhánh phức tạp theo document"""
    
    # Logic cho B5 - rất quan trọng
    if current_q == 'B5':
        answer = answers.get('B5')
        B1 = answers.get('B1')
        B2b = answers.get('B2b')
        B3 = answers.get('B3')
        B4 = answers.get('B4')
        
        # NẾU B1 VÀ B5 ĐƯỢC MÃ HÓA LÀ 1, CHUYỂN ĐẾN B15 (không có nhập viện và không tư vấn)
        if B1 == '1' and answer == '1':
            return 'B15'
        
        # NẾU B2b, B3 HOẶC B4 ĐƯỢC MÃ HÓA LÀ 5 VÀ B5 ĐƯỢC MÃ HÓA LÀ 1, CHUYỂN ĐẾN B9
        if answer == '1' and (B2b == '5' or B3 == '5' or B4 == '5'):
            return 'B9'
        
        # NẾU B2b, B3 VÀ B4 KHÔNG ĐƯỢC MÃ HÓA LÀ 5 VÀ B5 ĐƯỢC MÃ HÓA LÀ 1, CHUYỂN ĐẾN B18
        if answer == '1' and B2b != '5' and B3 != '5' and B4 != '5':
            return 'B18'
        
        # Nếu B5 = 5 (có gặp chuyên gia), chuyển đến B5a
        if answer == '5':
            return 'B5a'
    
    # Logic cho B5a - kiểm tra có tư vấn về mental health không
    if current_q == 'B5a':
        # Sau khi chọn chuyên gia, hỏi về số lần tư vấn
        return 'B6'
    
    # Logic cho B7 - kiểm tra có tư vấn về mental health không
    if current_q == 'B7':
        b7_answer = answers.get('B7', 0)
        # Nếu B7 > 0 (có tư vấn về mental health), hỏi B8 rồi B9
        if b7_answer and int(b7_answer) > 0:
            return 'B8'
        else:
            # Nếu B7 = 0 (không có tư vấn mental health), chuyển B18
            b2b = answers.get('B2b', '1')
            b3 = answers.get('B3', '1')
            b4 = answers.get('B4', '1')
            # Nếu có mental hospitalization thì hỏi B9, không thì B18
            if b2b == '5' or b3 == '5' or b4 == '5':
                return 'B9'
            else:
                return 'B18'
    
    # Logic cho B8 - sau khi hỏi lần tư vấn mental health
    if current_q == 'B8':
        # Chuyển đến B9 để hỏi loại giúp đỡ
        return 'B9'
    
    # Logic cho các câu B10-B17 phụ thuộc vào B9
    if current_q == 'B9':
        selected = answers.get('B9', [])
        if not selected:
            return 'B18'
        return 'B10'
    
    # B10 - kiểm tra có chọn 'info' trong B9 không
    if current_q == 'B10':
        b9_answers = answers.get('B9', [])
        if 'info' in b9_answers:
            return 'B10_1'
        else:
            return 'B10_2'
    
    if current_q == 'B10_1':
        return 'B10_1a'
    if current_q == 'B10_1a':
        if answers.get('B10_1a') == '1':  # Không đủ
            return 'B10_1b'
        else:
            return 'B11'
    if current_q == 'B10_1b':
        return 'B11'
    
    if current_q == 'B10_2':
        return 'B10_2a'
    if current_q == 'B10_2a':
        if answers.get('B10_2a') == '5':  # Có cần
            return 'B10_2b'
        else:
            return 'B11'
    if current_q == 'B10_2b':
        return 'B11'
    
    # B11 - kiểm tra có chọn 'medicine' trong B9 không
    if current_q == 'B11':
        b9_answers = answers.get('B9', [])
        if 'medicine' in b9_answers:
            return 'B11_1'
        else:
            return 'B11_2'
    
    if current_q == 'B11_1':
        return 'B11_1a'
    if current_q == 'B11_1a':
        if answers.get('B11_1a') == '1':
            return 'B11_1b'
        else:
            return 'B12'
    if current_q == 'B11_1b':
        return 'B12'
    
    if current_q == 'B11_2':
        return 'B11_2a'
    if current_q == 'B11_2a':
        if answers.get('B11_2a') == '5':
            return 'B11_2b'
        else:
            return 'B12'
    if current_q == 'B11_2b':
        return 'B12'
    
    # B12 - kiểm tra có chọn therapy trong B9 không
    if current_q == 'B12':
        b9_answers = answers.get('B9', [])
        has_therapy = 'psychotherapy' in b9_answers or 'cbt' in b9_answers or 'counselling' in b9_answers
        if has_therapy:
            return 'B12_1'
        else:
            return 'B12_2'
    
    if current_q == 'B12_1':
        return 'B12_1a'
    if current_q == 'B12_1a':
        if answers.get('B12_1a') == '1':
            return 'B12_1b'
        else:
            return 'B13'
    if current_q == 'B12_1b':
        return 'B13'
    
    if current_q == 'B12_2':
        return 'B12_2a'
    if current_q == 'B12_2a':
        if answers.get('B12_2a') == '5':
            return 'B12_2b'
        else:
            return 'B13'
    if current_q == 'B12_2b':
        return 'B13'
    
    # B13 - practical help
    if current_q == 'B13':
        b9_answers = answers.get('B9', [])
        if 'practical' in b9_answers:
            return 'B13_1'
        else:
            return 'B13_2'
    
    if current_q == 'B13_1':
        return 'B13_1a'
    if current_q == 'B13_1a':
        if answers.get('B13_1a') == '1':
            return 'B13_1b'
        else:
            return 'B14'
    if current_q == 'B13_1b':
        return 'B14'
    
    if current_q == 'B13_2':
        return 'B13_2a'
    if current_q == 'B13_2a':
        if answers.get('B13_2a') == '5':
            return 'B13_2b'
        else:
            return 'B14'
    if current_q == 'B13_2b':
        return 'B14'
    
    # B14 - work/selfcare
    if current_q == 'B14':
        b9_answers = answers.get('B9', [])
        has_work_selfcare = 'work' in b9_answers or 'selfcare' in b9_answers
        if has_work_selfcare:
            return 'B14_1'
        else:
            return 'B14_2'
    
    if current_q == 'B14_1':
        return 'B14_1a'
    if current_q == 'B14_1a':
        if answers.get('B14_1a') == '1':
            return 'B14_1b'
        else:
            return 'B15'
    if current_q == 'B14_1b':
        return 'B15'
    
    if current_q == 'B14_2':
        return 'B14_2a'
    if current_q == 'B14_2a':
        if answers.get('B14_2a') == '5':
            return 'B14_2b'
        else:
            return 'B15'
    if current_q == 'B14_2b':
        return 'B15'
    
    # B15 - work specific
    if current_q == 'B15':
        b9_answers = answers.get('B9', [])
        if 'work' in b9_answers:
            return 'B15_1'
        else:
            return 'B15_2'
    
    if current_q == 'B15_1':
        return 'B15_1a'
    if current_q == 'B15_1a':
        if answers.get('B15_1a') == '1':
            return 'B15_1b'
        else:
            return 'B16'
    if current_q == 'B15_1b':
        return 'B16'
    
    if current_q == 'B15_2':
        return 'B15_2a'
    if current_q == 'B15_2a':
        if answers.get('B15_2a') == '5':
            return 'B15_2b'
        else:
            return 'B16'
    if current_q == 'B15_2b':
        return 'B16'
    
    # B16 - selfcare specific
    if current_q == 'B16':
        b9_answers = answers.get('B9', [])
        if 'selfcare' in b9_answers:
            return 'B16_1'
        else:
            return 'B16_2'
    
    if current_q == 'B16_1':
        return 'B16_1a'
    if current_q == 'B16_1a':
        if answers.get('B16_1a') == '1':
            return 'B16_1b'
        else:
            return 'B17'
    if current_q == 'B16_1b':
        return 'B17'
    
    if current_q == 'B16_2':
        return 'B16_2a'
    if current_q == 'B16_2a':
        if answers.get('B16_2a') == '5':
            return 'B16_2b'
        else:
            return 'B17'
    if current_q == 'B16_2b':
        return 'B17'
    
    # B17 - social
    if current_q == 'B17':
        b9_answers = answers.get('B9', [])
        if 'social' in b9_answers:
            return 'B17_1'
        else:
            return 'B17_2'
    
    if current_q == 'B17_1':
        return 'B17_1a'
    if current_q == 'B17_1a':
        if answers.get('B17_1a') == '1':
            return 'B17_1b'
        else:
            return 'END'
    if current_q == 'B17_1b':
        return 'END'
    
    if current_q == 'B17_2':
        return 'B17_2a'
    if current_q == 'B17_2a':
        if answers.get('B17_2a') == '5':
            return 'B17_2b'
        else:
            return 'END'
    if current_q == 'B17_2b':
        return 'END'
    
    # Logic B18 - khi không có hospitalization/consultation
    if current_q == 'B18':
        # NẾU A1 VÀ A2 ĐƯỢC MÃ HÓA LÀ 1, KẾT THÚC
        A1 = answers.get('A1')
        A2 = answers.get('A2')
        if A1 == '1' and A2 == '1':
            return 'END'
        
        if answers.get('B18') == '1':  # Không cần
            return 'END'
        else:
            return 'B18_info'
    
    if current_q == 'B18_info':
        return 'B18_info_a' if answers.get('B18_info') == '5' else 'B19'
    if current_q == 'B18_info_a':
        return 'B19'
    
    if current_q == 'B19':
        return 'B19_a' if answers.get('B19') == '5' else 'B20'
    if current_q == 'B19_a':
        return 'B20'
    
    if current_q == 'B20':
        return 'B20_a' if answers.get('B20') == '5' else 'B21'
    if current_q == 'B20_a':
        return 'B21'
    
    if current_q == 'B21':
        return 'B21_a' if answers.get('B21') == '5' else 'B22'
    if current_q == 'B21_a':
        return 'B22'
    
    if current_q == 'B22':
        return 'B22_a' if answers.get('B22') == '5' else 'B23'
    if current_q == 'B22_a':
        return 'B23'
    
    if current_q == 'B23':
        return 'B23_a' if answers.get('B23') == '5' else 'B24'
    if current_q == 'B23_a':
        return 'B24'
    
    if current_q == 'B24':
        return 'B24_a' if answers.get('B24') == '5' else 'B25'
    if current_q == 'B24_a':
        return 'B25'
    
    if current_q == 'B25':
        return 'B25_a' if answers.get('B25') == '5' else 'END'
    if current_q == 'B25_a':
        return 'END'
    
    return None

# Cấu hình câu hỏi đầy đủ
SURVEY_CONFIG = {
    'A1': {
        'q': 'ANH/CHỊ CÓ PHẢI LÀ THÂN CHỦ HOẶC BỆNH NHÂN ĐÃ CÓ HIỂU BIẾT VỀ CÁC DỊCH VỤ SỨC KHỎE TÂM THẦN KHÔNG?',
        'type': 'radio',
        'opts': [('Có', '5'), ('Không', '1')],
        'next': 'A2'
    },
    'A2': {
        'q': 'Hãy nghĩ lại trong năm vừa rồi, và xem xét liệu bạn có gặp bất cứ khó khăn nào liên quan đến vấn đề sức khỏe tâm thần của mình trong thời gian đó không: Bạn có nghĩ rằng, trong năm vừa rồi, bạn đã có bất cứ lúc nào gặp phải các vấn đề với sức khỏe tâm thần của bản thân không?',
        'type': 'radio',
        'opts': [('Có', '5'), ('Không', '1')],
        'next_logic': lambda a: 'A3' if a == '5' else 'B1'
    },
    'A3': {
        'q': 'Bạn sẽ gọi vấn đề hoặc những vấn đề mà bạn gặp phải liên quan đến sức khỏe tâm thần của mình là gì?',
        'type': 'textarea',
        'note': '(THĂM DÒ NẾU CẦN THIẾT. THÔNG TIN CÓ THỂ ĐƯỢC THÊM VÀO ĐÂY TỪ CÁC CÂU TRẢ LỜI TRƯỚC ĐÓ TRONG CUỘC PHỎNG VẤN. TẠO VÀ GHI LẠI MỘT MÔ TẢ VỀ CÁC VẤN ĐỀ SỨC KHỎE TÂM THẦN ĐÃ TRẢI QUA MÀ ĐỐI TƯỢNG SẼ CẢM THẤY QUEN THUỘC)',
        'next': 'B1'
    },
    'B1': {
        'q': 'Trong 12 tháng qua bạn đã bao giờ từng nhập viện ít nhất là một đêm tại bất kỳ bệnh viện nào không?',
        'type': 'radio',
        'opts': [('Có', '5'), ('Không', '1')],
        'next_logic': lambda a: 'B2' if a == '5' else 'B5'
    },
    'B2': {
        'q': 'Bạn đã bao giờ từng nhập viện qua đêm tại một bệnh viện đa khoa không?',
        'type': 'radio',
        'opts': [('Có', '5'), ('Không', '1')],
        'next_logic': lambda a: 'B2a' if a == '5' else 'B3'
    },
    'B2a': {
        'q': 'Việc bạn nhập viện đó có phải là do bệnh lý về thể chất hay không?',
        'type': 'radio',
        'opts': [('Có', '5'), ('Không', '1')],
        'next_logic': lambda a: 'B2a1' if a == '5' else 'B2b'
    },
    'B2a1': {
        'q': 'Trong 12 tháng vừa rồi, đã có bao nhiêu lần bạn nhập viện ít nhất một đêm tại bệnh viện đa khoa do bệnh lý về thể chất?',
        'type': 'number',
        'next': 'B2a2'
    },
    'B2a2': {
        'q': '(Đối với lần nhập viện đó/trong những lần nhập viện đó), tổng cộng bạn đã ở lại bao nhiêu đêm tại bệnh viện đa khoa do bệnh lý về thể chất?',
        'type': 'number',
        'next': 'B2b'
    },
    'B2b': {
        'q': 'Bạn đã bao giờ từng nhập viện qua đêm tại một bệnh viện đa khoa do các vấn đề thần kinh hoặc tâm thần gây ra trong vòng 12 tháng qua không?',
        'type': 'radio',
        'opts': [('Có', '5'), ('Không', '1')],
        'next_logic': lambda a: 'B2b1' if a == '5' else 'B3'
    },
    'B2b1': {
        'q': 'Trong vòng 12 tháng qua, đã có bao nhiêu lần bạn từng nhập viện ít nhất một đêm tại bệnh viện đa khoa do các vấn đề thần kinh hoặc tâm thần gây ra?',
        'type': 'number',
        'next': 'B2b2'
    },
    'B2b2': {
        'q': 'Đối với lần nhập viện đó/trong những lần nhập viện đó, tổng cộng bạn đã ở lại bao nhiêu đêm tại bệnh viện đa khoa vì ảnh hưởng của các vấn đề thần kinh hoặc tâm thần?',
        'type': 'number',
        'next': 'B2b3'
    },
    'B2b3': {
        'q': 'Bạn đã nằm giường hạng dịch vụ hay phổ thông?',
        'type': 'radio',
        'opts': [('Dịch vụ (tư nhân)', 'private'), ('Phổ thông (công)', 'public')],
        'next': 'B3'
    },
    'B3': {
        'q': 'Trong 12 tháng vừa rồi bạn đã từng nhập viện qua đêm tại một bệnh viện tâm thần không?',
        'type': 'radio',
        'opts': [('Có', '5'), ('Không', '1')],
        'next_logic': lambda a: 'B3a1' if a == '5' else 'B4'
    },
    'B3a1': {
        'q': 'Trong vòng 12 tháng qua, đã bao nhiêu lần bạn nhập viện ít nhất một đêm tại bệnh viện tâm thần?',
        'type': 'number',
        'next': 'B3a2'
    },
    'B3a2': {
        'q': 'Tổng cộng bạn đã ở lại bao nhiêu đêm tại bệnh viện tâm thần?',
        'type': 'number',
        'next': 'B3a3'
    },
    'B3a3': {
        'q': 'Đó là bệnh viện tâm thần thuộc tư nhân hay Nhà Nước?',
        'type': 'radio',
        'opts': [('Tư nhân', 'private'), ('Nhà Nước', 'public')],
        'next': 'B4'
    },
    'B4': {
        'q': 'Trong 12 tháng vừa rồi bạn đã từng nhập viện qua đêm tại bất kỳ đơn vị cai nghiện ma túy và rượu bia nào ở bệnh viện không?',
        'type': 'radio',
        'opts': [('Có', '5'), ('Không', '1')],
        'next_logic': lambda a: 'B4a1' if a == '5' else 'B5'
    },
    'B4a1': {
        'q': 'Trong vòng 12 tháng qua, đã có bao nhiêu lần bạn nhập viện ít nhất một đêm tại các đơn vị cai nghiện ma túy và rượu bia?',
        'type': 'number',
        'next': 'B4a2'
    },
    'B4a2': {
        'q': '(Đối với lần nhập viện đó/Trong những lần nhập viện đó), tổng cộng bạn đã ở lại bao nhiêu đêm tại các đơn vị cai nghiện ma túy và rượu bia?',
        'type': 'number',
        'next': 'B4a3'
    },
    'B4a3': {
        'q': 'Đó là đơn vị thuộc tư nhân hay Nhà Nước?',
        'type': 'radio',
        'opts': [('Tư nhân', 'private'), ('Nhà Nước', 'public')],
        'next': 'B5'
    },
    'B5': {
        'q': 'Trong 12 tháng qua, (ngoài thời gian bạn đã ở bệnh viện), bạn có gặp bất kỳ bác sĩ hoặc chuyên gia y tế thuộc các lĩnh vực được liệt kê liên quan đến tình trạng sức khỏe của chính bạn không?',
        'type': 'radio',
        'note': 'Các chuyên gia y tế bao gồm: Bác sĩ đa khoa, Bác sĩ chuyên khoa, Bác sĩ tâm thần, Nhà tâm lý học, Nhân viên công tác xã hội, Tư vấn viên, Điều dưỡng/Y tá, v.v.',
        'opts': [('Có', '5'), ('Không', '1')],
        'next': None  # Logic phức tạp
    },
    'B5a': {
        'q': 'Bạn đã gặp những chuyên gia y tế nào được liệt kê? (Chọn tất cả các đáp án phù hợp)',
        'type': 'checkbox',
        'opts': [
            ('Bác sĩ đa khoa', '1'),
            ('Bác sĩ chẩn đoán hình ảnh hoặc chuyên khoa X-quang, v.v.', '2'),
            ('Bác sĩ bệnh lý học hoặc chuyên khoa xét nghiệm máu v.v.', '3'),
            ('Bác sĩ nội khoa hoặc chuyên viên y tế khác', '4'),
            ('Bác sĩ phẫu thuật hoặc bác sĩ phụ khoa', '5'),
            ('Bác sĩ tâm thần', '6'),
            ('Nhà tâm lý học', '7'),
            ('Nhân viên công tác xã hội hoặc cán bộ phụ trách phúc lợi', '8'),
            ('Tư vấn viên về tình trạng nghiện chất', '9'),
            ('Các tư vấn viên khác', '10'),
            ('Điều dưỡng/Y tá', '11'),
            ('Nhóm chuyên gia sức khỏe tâm thần', '12'),
            ('Dược sĩ tư vấn chuyên môn', '13'),
            ('Nhân viên xe cứu thương', '14'),
            ('Các chuyên gia y tế khác, xin vui lòng ghi rõ', '15')
        ],
        'next': 'B6'
    },
    'B6': {
        'q': 'Bạn đã tham gia tiến trình tư vấn sức khỏe với (TÊN CHUYÊN GIA Y TẾ) bao nhiêu lần trong vòng 12 tháng qua?',
        'type': 'number',
        'note': 'NV: SỐ LẦN TƯƠNG ĐƯƠNG VỚI SỐ LẦN ĐI KHÁM',
        'next': 'B7'
    },
    'B7': {
        'q': 'Có bao nhiêu trong số những lần tham vấn này liên quan đến các vấn đề tâm thần dưới bất kỳ hình thức nào?',
        'type': 'number',
        'note': '[NẾU SỐ NÀY >0, BẠN HÃY HỎI MỤC B9 KHI BẠN ĐẾN CÂU ĐÓ]',
        'next': None  # Logic phức tạp
    },
    'B8': {
        'q': 'Những buổi tư vấn về sức khỏe tâm thần đó chủ yếu diễn ra ở đâu?',
        'type': 'radio',
        'note': 'MÃ HÓA CÂU TRẢ LỜI CỦA NGHIỆM THỂ THEO CÁC MÃ ĐỊA ĐIỂM SAU ĐÂY',
        'opts': [
            ('Phòng khám tư nhân', '1'),
            ('Bệnh viện công/Bệnh viện tâm thần', '2'),
            ('Trung tâm sức khỏe cộng đồng', '3'),
            ('Nhà (tư vấn qua điện thoại/trực tuyến)', '4'),
            ('Khác', '5')
        ],
        'next': 'B9'
    },
    'B6_B8_check': {
        'q': 'Cảm ơn bạn đã cung cấp thông tin',
        'type': 'info',
        'next': None  # Removed - no longer needed
    },
    'B6_B8_check': {
        'q': 'Cảm ơn bạn đã cung cấp thông tin về các lần tư vấn',
        'type': 'info',
        'next': None  # Logic phức tạp
    },
    'B9': {
        'q': 'dynamic',  # Will be set dynamically in render_question
        'type': 'checkbox',
        'opts': [
            ('Thông tin về bệnh tâm thần, các phương pháp điều trị và các dịch vụ hiện hành có sẵn?', 'info'),
            ('Thuốc hoặc viên uống dạng nén?', 'medicine'),
            ('Tâm lý trị liệu - thảo luận về các vấn đề nguyên nhân bắt nguồn từ quá khứ của bạn?', 'psychotherapy'),
            ('Liệu pháp nhận thức hành vi - học cách để thay đổi suy nghĩ, hành vi và cảm xúc của bạn?', 'cbt'),
            ('Tham vấn - giúp nói chuyện để giải quyết các vấn đề của bạn.', 'counselling'),
            ('Giúp giải quyết các vấn đề thực tế, chẳng hạn như nhà ở hoặc tiền bạc?', 'practical'),
            ('Giúp cải thiện khả năng làm việc, hoặc sử dụng thời gian của bạn theo những cách khác nhau một cách hiệu quả hơn?', 'work'),
            ('Giúp bạn cải thiện khả năng tự chăm sóc bản thân hoặc nhà cửa.', 'selfcare'),
            ('Giúp bạn gặp gỡ kết nối với mọi người để được hỗ trợ và có người đồng hành?', 'social'),
            ('Khác – ví dụ rõ: ______________________________________.', 'other')
        ],
        'next': None  # Logic phức tạp
    },
    # Router questions for B10-B17 (these determine which branch to take)
    'B10': {
        'q': 'B10 - Thông tin giúp đỡ',
        'type': 'info',
        'next': None  # Logic handles this
    },
    'B11': {
        'q': 'B11 - Thuốc hoặc viên uống',
        'type': 'info',
        'next': None  # Logic handles this
    },
    'B12': {
        'q': 'B12 - Tâm lý trị liệu/liệu pháp trò chuyện',
        'type': 'info',
        'next': None  # Logic handles this
    },
    'B13': {
        'q': 'B13 - Giúp đỡ thực tế',
        'type': 'info',
        'next': None  # Logic handles this
    },
    'B14': {
        'q': 'B14 - Giúp đỡ công việc/tự chăm sóc',
        'type': 'info',
        'next': None  # Logic handles this
    },
    'B15': {
        'q': 'B15 - Giúp đỡ công việc (cụ thể)',
        'type': 'info',
        'next': None  # Logic handles this
    },
    'B16': {
        'q': 'B16 - Giúp đỡ tự chăm sóc (cụ thể)',
        'type': 'info',
        'next': None  # Logic handles this
    },
    'B17': {
        'q': 'B17 - Giúp đỡ kết nối xã hội',
        'type': 'info',
        'next': None  # Logic handles this
    },
    'B10_1': {
        'q': 'Bạn đã đề cập rằng bạn đã nhận được thông tin về bệnh tâm thần, các phương pháp điều trị và các dịch vụ có sẵn.',
        'type': 'info',
        'next': 'B10_1a'
    },
    'B10_1a': {
        'q': 'Bạn có nghĩ rằng bạn đã nhận được đủ sự giúp đỡ kiểu này tương ứng với nhu cầu của bản thân không?',
        'type': 'radio',
        'opts': [('Không đủ', '1'), ('Đủ', '5')],
        'next': None
    },
    'B10_1b': {
        'q': 'Tại sao bạn lại không nhận được nhiều sự giúp đỡ hơn từ các chuyên gia y tế? Vui lòng chọn lý do chính, hoặc một lý do phù hợp nhất với bạn.',
        'type': 'radio',
        'opts': [
            ('Tôi muốn tự mình xoay xở', '1'),
            ('Tôi không nghĩ có bất cứ điều gì khác có thể giúp ích', '2'),
            ('Tôi không biết làm thế nào hoặc ở đâu để nhận được nhiều sự giúp đỡ hơn', '3'),
            ('Tôi e ngại trong việc yêu cầu giúp đỡ thêm, hoặc lo sợ việc người khác sẽ nghĩ gì về tôi nếu tôi làm vậy', '4'),
            ('Tôi không đủ khả năng chi trả tiền bạc', '5'),
            ('Tôi đã thử yêu cầu nhưng không nhận được sự giúp đỡ', '6'),
            ('Tôi đã nhận được sự giúp đỡ từ nguồn khác', '7')
        ],
        'next': 'B11'
    },
    'B10_2': {
        'q': 'Bạn đã đề cập rằng bạn không nhận được thông tin về bệnh tâm thần, việc điều trị và các dịch vụ có sẵn.',
        'type': 'info',
        'next': 'B10_2a'
    },
    'B10_2a': {
        'q': 'Bạn có nghĩ rằng bạn cần giúp đỡ theo kiểu này không?',
        'type': 'radio',
        'opts': [('Không cần', '1'), ('Có cần', '5')],
        'next': None
    },
    'B10_2b': {
        'q': 'Tại sao bạn không nhận sự giúp đỡ này? Vui lòng chọn lý do chính, hoặc một lý do phù hợp nhất với bạn.',
        'type': 'radio',
        'opts': [
            ('Tôi muốn tự mình xoay xở', '1'),
            ('Tôi không nghĩ có bất cứ điều gì có thể giúp ích cho bản thân', '2'),
            ('Tôi không biết nhận sự giúp đỡ ở đâu', '3'),
            ('Tôi e ngại trong việc yêu cầu giúp đỡ, hoặc lo sợ việc người khác sẽ nghĩ gì về tôi nếu tôi làm vậy', '4'),
            ('Tôi không đủ khả năng chi trả tiền bạc', '5'),
            ('Tôi đã thử yêu cầu nhưng không nhận được sự giúp đỡ', '6'),
            ('Tôi đã nhận được sự giúp đỡ từ nguồn khác', '7')
        ],
        'next': 'B11'
    },
    # B11 - Medicine questions (tương tự B10)
    'B11_1': {
        'q': 'Bạn đã đề cập rằng bạn đã nhận được thuốc hoặc viên uống.',
        'type': 'info',
        'next': 'B11_1a'
    },
    'B11_1a': {
        'q': 'Bạn có nghĩ rằng bạn đã nhận được đủ sự giúp đỡ kiểu này từ các chuyên gia y tế không?',
        'type': 'radio',
        'opts': [('Không đủ', '1'), ('Đủ', '5')],
        'next': None
    },
    'B11_1b': {
        'q': 'Tại sao bạn lại không nhận được nhiều sự giúp đỡ hơn từ các chuyên gia y tế? Vui lòng chọn lý do chính, hoặc một lý do phù hợp nhất với bạn.',
        'type': 'radio',
        'opts': [
            ('Tôi muốn tự mình xoay xở', '1'),
            ('Tôi không nghĩ có bất cứ điều gì khác có thể giúp ích', '2'),
            ('Tôi không biết làm thế nào hoặc ở đâu để nhận được nhiều sự giúp đỡ hơn', '3'),
            ('Tôi e ngại trong việc yêu cầu giúp đỡ thêm, hoặc lo sợ việc người khác sẽ nghĩ gì về tôi nếu tôi làm vậy', '4'),
            ('Tôi không đủ khả năng chi trả tiền bạc', '5'),
            ('Tôi đã thử yêu cầu nhưng không nhận được sự giúp đỡ', '6'),
            ('Tôi đã nhận được sự giúp đỡ từ nguồn khác', '7')
        ],
        'next': 'B12'
    },
    'B11_2': {
        'q': 'Bạn đã đề cập rằng bạn không nhận được thuốc hoặc viên uống dạng nén.',
        'type': 'info',
        'next': 'B11_2a'
    },
    'B11_2a': {
        'q': 'Bạn có nghĩ rằng bạn cần giúp đỡ theo kiểu này không?',
        'type': 'radio',
        'opts': [('Không cần', '1'), ('Có cần', '5')],
        'next': None
    },
    'B11_2b': {
        'q': 'Tại sao bạn không nhận sự giúp đỡ này? Vui lòng chọn lý do chính, hoặc một lý do phù hợp nhất với bạn.',
        'type': 'radio',
        'opts': [
            ('Tôi muốn tự mình xoay xở', '1'),
            ('Tôi không nghĩ có bất cứ điều gì có thể giúp ích cho bản thân', '2'),
            ('Tôi không biết nhận sự giúp đỡ ở đâu', '3'),
            ('Tôi e ngại trong việc yêu cầu giúp đỡ, hoặc lo sợ việc người khác sẽ nghĩ gì về tôi nếu tôi làm vậy', '4'),
            ('Tôi không đủ khả năng chi trả tiền bạc', '5'),
            ('Tôi đã thử yêu cầu nhưng không nhận được sự giúp đỡ', '6'),
            ('Tôi đã nhận được sự giúp đỡ từ nguồn khác', '7')
        ],
        'next': 'B12'
    },
    'B12_1': {
        'q': 'Bạn đã đề cập rằng bạn đã nhận được dịch vụ tham vấn hoặc một liệu pháp trò chuyện.',
        'type': 'info',
        'next': 'B12_1a'
    },
    'B12_1a': {
        'q': 'Bạn có nghĩ rằng bạn đã nhận được đủ sự giúp đỡ kiểu này từ các chuyên gia y tế không?',
        'type': 'radio',
        'opts': [('Không đủ', '1'), ('Đủ', '5')],
        'next': None
    },
    'B12_1b': {
        'q': 'Tại sao bạn lại không nhận được nhiều sự giúp đỡ hơn từ các chuyên gia y tế? Vui lòng chọn lý do chính, hoặc một lý do phù hợp nhất với bạn.',
        'type': 'radio',
        'opts': [
            ('Tôi muốn tự mình xoay xở', '1'),
            ('Tôi không nghĩ có bất cứ điều gì khác có thể giúp ích', '2'),
            ('Tôi không biết làm thế nào hoặc ở đâu để nhận được nhiều sự giúp đỡ hơn', '3'),
            ('Tôi e ngại trong việc yêu cầu giúp đỡ thêm, hoặc lo sợ việc người khác sẽ nghĩ gì về tôi nếu tôi làm vậy', '4'),
            ('Tôi không đủ khả năng chi trả tiền bạc', '5'),
            ('Tôi đã thử yêu cầu nhưng không nhận được sự giúp đỡ', '6'),
            ('Tôi đã nhận được sự giúp đỡ từ nguồn khác', '7')
        ],
        'next': 'B13'
    },
    'B12_2': {
        'q': 'Bạn đã đề cập rằng bạn không nhận được dịch vụ tham vấn hoặc một liệu pháp trò chuyện.',
        'type': 'info',
        'next': 'B12_2a'
    },
    'B12_2a': {
        'q': 'Bạn có nghĩ rằng bạn cần giúp đỡ theo kiểu này không?',
        'type': 'radio',
        'opts': [('Không cần', '1'), ('Có cần', '5')],
        'next': None
    },
    'B12_2b': {
        'q': 'Tại sao bạn không nhận sự giúp đỡ này? Vui lòng chọn lý do chính, hoặc một lý do phù hợp nhất với bạn.',
        'type': 'radio',
        'opts': [
            ('Tôi muốn tự mình xoay xở', '1'),
            ('Tôi không nghĩ có bất cứ điều gì có thể giúp ích cho bản thân', '2'),
            ('Tôi không biết nhận sự giúp đỡ ở đâu', '3'),
            ('Tôi e ngại trong việc yêu cầu giúp đỡ, hoặc lo sợ việc người khác sẽ nghĩ gì về tôi nếu tôi làm vậy', '4'),
            ('Tôi không đủ khả năng chi trả tiền bạc', '5'),
            ('Tôi đã thử yêu cầu nhưng không nhận được sự giúp đỡ', '6'),
            ('Tôi đã nhận được sự giúp đỡ từ nguồn khác', '7')
        ],
        'next': 'B13'
    },
    'B13_1': {
        'q': 'Bạn đã đề cập rằng bạn nhận được sự giúp đỡ để giải quyết các vấn đề thực tế như nhà ở hoặc tiền bạc.',
        'type': 'info',
        'next': 'B13_1a'
    },
    'B13_1a': {
        'q': 'Bạn có nghĩ rằng bạn đã nhận được đủ sự giúp đỡ kiểu này từ các chuyên gia y tế không?',
        'type': 'radio',
        'opts': [('Không đủ', '1'), ('Đủ', '5')],
        'next': None
    },
    'B13_1b': {
        'q': 'Tại sao bạn lại không nhận được nhiều sự giúp đỡ hơn từ các chuyên gia y tế? Vui lòng chọn lý do chính, hoặc một lý do phù hợp nhất với bạn.',
        'type': 'radio',
        'opts': [
            ('Tôi muốn tự mình xoay xở', '1'),
            ('Tôi không nghĩ có bất cứ điều gì khác có thể giúp ích', '2'),
            ('Tôi không biết làm thế nào hoặc ở đâu để nhận được nhiều sự giúp đỡ hơn', '3'),
            ('Tôi e ngại trong việc yêu cầu giúp đỡ thêm, hoặc lo sợ việc người khác sẽ nghĩ gì về tôi nếu tôi làm vậy', '4'),
            ('Tôi không đủ khả năng chi trả tiền bạc', '5'),
            ('Tôi đã thử yêu cầu nhưng không nhận được sự giúp đỡ', '6'),
            ('Tôi đã nhận được sự giúp đỡ từ nguồn khác', '7')
        ],
        'next': 'B14'
    },
    'B13_2': {
        'q': 'Bạn đã đề cập rằng bạn không nhận được sự giúp đỡ để giải quyết các vấn đề thực tế như nhà ở hoặc tiền bạc.',
        'type': 'info',
        'next': 'B13_2a'
    },
    'B13_2a': {
        'q': 'Bạn có nghĩ rằng bạn cần giúp đỡ theo kiểu này không?',
        'type': 'radio',
        'opts': [('Không cần', '1'), ('Có cần', '5')],
        'next': None
    },
    'B13_2b': {
        'q': 'Tại sao bạn không nhận sự giúp đỡ này? Vui lòng chọn lý do chính, hoặc một lý do phù hợp nhất với bạn.',
        'type': 'radio',
        'opts': [
            ('Tôi muốn tự mình xoay xở', '1'),
            ('Tôi không nghĩ có bất cứ điều gì có thể giúp ích cho bản thân', '2'),
            ('Tôi không biết nhận sự giúp đỡ ở đâu', '3'),
            ('Tôi e ngại trong việc yêu cầu giúp đỡ, hoặc lo sợ việc người khác sẽ nghĩ gì về tôi nếu tôi làm vậy', '4'),
            ('Tôi không đủ khả năng chi trả tiền bạc', '5'),
            ('Tôi đã thử yêu cầu nhưng không nhận được sự giúp đỡ', '6'),
            ('Tôi đã nhận được sự giúp đỡ từ nguồn khác', '7')
        ],
        'next': 'B14'
    },
    'B14_1': {
        'q': 'Bạn đã đề cập rằng bạn nhận được sự giúp đỡ để cải thiện khả năng làm việc, tự chăm sóc bản thân hoặc sử dụng thời gian.',
        'type': 'info',
        'next': 'B14_1a'
    },
    'B14_1a': {
        'q': 'Bạn có nghĩ rằng bạn đã nhận được đủ sự giúp đỡ kiểu này từ các chuyên gia y tế không?',
        'type': 'radio',
        'opts': [('Không đủ', '1'), ('Đủ', '5')],
        'next': None
    },
    'B14_1b': {
        'q': 'Tại sao bạn lại không nhận được nhiều sự giúp đỡ hơn từ các chuyên gia y tế? Vui lòng chọn lý do chính, hoặc một lý do phù hợp nhất với bạn.',
        'type': 'radio',
        'opts': [
            ('Tôi muốn tự mình xoay xở', '1'),
            ('Tôi không nghĩ có bất cứ điều gì khác có thể giúp ích', '2'),
            ('Tôi không biết làm thế nào hoặc ở đâu để nhận được nhiều sự giúp đỡ hơn', '3'),
            ('Tôi e ngại trong việc yêu cầu giúp đỡ thêm, hoặc lo sợ việc người khác sẽ nghĩ gì về tôi nếu tôi làm vậy', '4'),
            ('Tôi không đủ khả năng chi trả tiền bạc', '5'),
            ('Tôi đã thử yêu cầu nhưng không nhận được sự giúp đỡ', '6'),
            ('Tôi đã nhận được sự giúp đỡ từ nguồn khác', '7')
        ],
        'next': 'B15'
    },
    'B14_2': {
        'q': 'Bạn đã đề cập rằng bạn không nhận được sự giúp đỡ để cải thiện khả năng làm việc, tự chăm sóc bản thân hoặc sử dụng thời gian.',
        'type': 'info',
        'next': 'B14_2a'
    },
    'B14_2a': {
        'q': 'Bạn có nghĩ rằng bạn cần giúp đỡ theo kiểu này không?',
        'type': 'radio',
        'opts': [('Không cần', '1'), ('Có cần', '5')],
        'next': None
    },
    'B14_2b': {
        'q': 'Tại sao bạn không nhận sự giúp đỡ này? Vui lòng chọn lý do chính, hoặc một lý do phù hợp nhất với bạn.',
        'type': 'radio',
        'opts': [
            ('Tôi muốn tự mình xoay xở', '1'),
            ('Tôi không nghĩ có bất cứ điều gì có thể giúp ích cho bản thân', '2'),
            ('Tôi không biết nhận sự giúp đỡ ở đâu', '3'),
            ('Tôi e ngại trong việc yêu cầu giúp đỡ, hoặc lo sợ việc người khác sẽ nghĩ gì về tôi nếu tôi làm vậy', '4'),
            ('Tôi không đủ khả năng chi trả tiền bạc', '5'),
            ('Tôi đã thử yêu cầu nhưng không nhận được sự giúp đỡ', '6'),
            ('Tôi đã nhận được sự giúp đỡ từ nguồn khác', '7')
        ],
        'next': 'B15'
    },
    'B15_1': {
        'q': 'Cụ thể bạn đã đề cập rằng bạn nhận được sự giúp đỡ để cải thiện khả năng làm việc, hoặc sử dụng thời gian của bạn theo những cách khác nhau.',
        'type': 'info',
        'next': 'B15_1a'
    },
    'B15_1a': {
        'q': 'Bạn có nghĩ rằng bạn đã nhận được đủ sự giúp đỡ kiểu này từ các chuyên gia y tế không?',
        'type': 'radio',
        'opts': [('Không đủ', '1'), ('Đủ', '5')],
        'next': None
    },
    'B15_1b': {
        'q': 'Tại sao bạn lại không nhận được nhiều sự giúp đỡ hơn từ các chuyên gia y tế? Vui lòng chọn lý do chính, hoặc một lý do phù hợp nhất với bạn.',
        'type': 'radio',
        'opts': [
            ('Tôi muốn tự mình xoay xở', '1'),
            ('Tôi không nghĩ có bất cứ điều gì khác có thể giúp ích', '2'),
            ('Tôi không biết làm thế nào hoặc ở đâu để nhận được nhiều sự giúp đỡ hơn', '3'),
            ('Tôi e ngại trong việc yêu cầu giúp đỡ thêm, hoặc lo sợ việc người khác sẽ nghĩ gì về tôi nếu tôi làm vậy', '4'),
            ('Tôi không đủ khả năng chi trả tiền bạc', '5'),
            ('Tôi đã thử yêu cầu nhưng không nhận được sự giúp đỡ', '6'),
            ('Tôi đã nhận được sự giúp đỡ từ nguồn khác', '7')
        ],
        'next': 'B16'
    },
    'B15_2': {
        'q': 'Cụ thể bạn đã đề cập rằng bạn không nhận được sự giúp đỡ để cải thiện khả năng làm việc, hoặc sử dụng thời gian của bạn theo những cách khác nhau.',
        'type': 'info',
        'next': 'B15_2a'
    },
    'B15_2a': {
        'q': 'Bạn có nghĩ rằng bạn cần giúp đỡ theo kiểu này không?',
        'type': 'radio',
        'opts': [('Không cần', '1'), ('Có cần', '5')],
        'next': None
    },
    'B15_2b': {
        'q': 'Tại sao bạn không nhận sự giúp đỡ này? Vui lòng chọn lý do chính, hoặc một lý do phù hợp nhất với bạn.',
        'type': 'radio',
        'opts': [
            ('Tôi muốn tự mình xoay xở', '1'),
            ('Tôi không nghĩ có bất cứ điều gì có thể giúp ích cho bản thân', '2'),
            ('Tôi không biết nhận sự giúp đỡ ở đâu', '3'),
            ('Tôi e ngại trong việc yêu cầu giúp đỡ, hoặc lo sợ việc người khác sẽ nghĩ gì về tôi nếu tôi làm vậy', '4'),
            ('Tôi không đủ khả năng chi trả tiền bạc', '5'),
            ('Tôi đã thử yêu cầu nhưng không nhận được sự giúp đỡ', '6'),
            ('Tôi đã nhận được sự giúp đỡ từ nguồn khác', '7')
        ],
        'next': 'B16'
    },
    'B16_1': {
        'q': 'Cụ thể bạn đã đề cập rằng bạn nhận được sự giúp đỡ để cải thiện khả năng tự chăm sóc bản thân hoặc nhà cửa của bạn.',
        'type': 'info',
        'next': 'B16_1a'
    },
    'B16_1a': {
        'q': 'Bạn có nghĩ rằng bạn đã nhận được đủ sự giúp đỡ kiểu này từ các chuyên gia y tế không?',
        'type': 'radio',
        'opts': [('Không đủ', '1'), ('Đủ', '5')],
        'next': None
    },
    'B16_1b': {
        'q': 'Tại sao bạn lại không nhận được nhiều sự giúp đỡ hơn từ các chuyên gia y tế? Vui lòng chọn lý do chính, hoặc một lý do phù hợp nhất với bạn.',
        'type': 'radio',
        'opts': [
            ('Tôi muốn tự mình xoay xở', '1'),
            ('Tôi không nghĩ có bất cứ điều gì khác có thể giúp ích', '2'),
            ('Tôi không biết làm thế nào hoặc ở đâu để nhận được nhiều sự giúp đỡ hơn', '3'),
            ('Tôi e ngại trong việc yêu cầu giúp đỡ thêm, hoặc lo sợ việc người khác sẽ nghĩ gì về tôi nếu tôi làm vậy', '4'),
            ('Tôi không đủ khả năng chi trả tiền bạc', '5'),
            ('Tôi đã thử yêu cầu nhưng không nhận được sự giúp đỡ', '6'),
            ('Tôi đã nhận được sự giúp đỡ từ nguồn khác', '7')
        ],
        'next': 'B17'
    },
    'B16_2': {
        'q': 'Cụ thể bạn đã đề cập rằng bạn không nhận được sự giúp đỡ để cải thiện khả năng tự chăm sóc bản thân hoặc nhà cửa của bạn.',
        'type': 'info',
        'next': 'B16_2a'
    },
    'B16_2a': {
        'q': 'Bạn có nghĩ rằng bạn cần giúp đỡ theo kiểu này không?',
        'type': 'radio',
        'opts': [('Không cần', '1'), ('Có cần', '5')],
        'next': None
    },
    'B16_2b': {
        'q': 'Tại sao bạn không nhận sự giúp đỡ này? Vui lòng chọn lý do chính, hoặc một lý do phù hợp nhất với bạn.',
        'type': 'radio',
        'opts': [
            ('Tôi muốn tự mình xoay xở', '1'),
            ('Tôi không nghĩ có bất cứ điều gì có thể giúp ích cho bản thân', '2'),
            ('Tôi không biết nhận sự giúp đỡ ở đâu', '3'),
            ('Tôi e ngại trong việc yêu cầu giúp đỡ, hoặc lo sợ việc người khác sẽ nghĩ gì về tôi nếu tôi làm vậy', '4'),
            ('Tôi không đủ khả năng chi trả tiền bạc', '5'),
            ('Tôi đã thử yêu cầu nhưng không nhận được sự giúp đỡ', '6'),
            ('Tôi đã nhận được sự giúp đỡ từ nguồn khác', '7')
        ],
        'next': 'B17'
    },
    'B17_1': {
        'q': 'Bạn đã đề cập rằng bạn nhận được sự giúp đỡ để gặp gỡ kết nối với mọi người để được hỗ trợ và có người đồng hành.',
        'type': 'info',
        'next': 'B17_1a'
    },
    'B17_1a': {
        'q': 'Bạn có nghĩ rằng bạn đã nhận được đủ sự giúp đỡ kiểu này từ các chuyên gia y tế không?',
        'type': 'radio',
        'opts': [('Không đủ', '1'), ('Đủ', '5')],
        'next': None
    },
    'B17_1b': {
        'q': 'Tại sao bạn lại không nhận được nhiều sự giúp đỡ hơn từ các chuyên gia y tế? Vui lòng chọn lý do chính, hoặc một lý do phù hợp nhất với bạn.',
        'type': 'radio',
        'opts': [
            ('Tôi muốn tự mình xoay xở', '1'),
            ('Tôi không nghĩ có bất cứ điều gì khác có thể giúp ích', '2'),
            ('Tôi không biết làm thế nào hoặc ở đâu để nhận được nhiều sự giúp đỡ hơn', '3'),
            ('Tôi e ngại trong việc yêu cầu giúp đỡ thêm, hoặc lo sợ việc người khác sẽ nghĩ gì về tôi nếu tôi làm vậy', '4'),
            ('Tôi không đủ khả năng chi trả tiền bạc', '5'),
            ('Tôi đã thử yêu cầu nhưng không nhận được sự giúp đỡ', '6'),
            ('Tôi đã nhận được sự giúp đỡ từ nguồn khác', '7')
        ],
        'next': 'END'
    },
    'B17_2': {
        'q': 'Bạn đã đề cập rằng bạn không nhận được sự giúp đỡ để gặp gỡ kết nối với mọi người để được hỗ trợ và có người đồng hành.',
        'type': 'info',
        'next': 'B17_2a'
    },
    'B17_2a': {
        'q': 'Bạn có nghĩ rằng bạn cần giúp đỡ theo kiểu này không?',
        'type': 'radio',
        'opts': [('Không cần', '1'), ('Có cần', '5')],
        'next': None
    },
    'B17_2b': {
        'q': 'Tại sao bạn không nhận sự giúp đỡ này? Vui lòng chọn lý do chính, hoặc một lý do phù hợp nhất với bạn.',
        'type': 'radio',
        'opts': [
            ('Tôi muốn tự mình xoay xở', '1'),
            ('Tôi không nghĩ có bất cứ điều gì có thể giúp ích cho bản thân', '2'),
            ('Tôi không biết nhận sự giúp đỡ ở đâu', '3'),
            ('Tôi e ngại trong việc yêu cầu giúp đỡ, hoặc lo sợ việc người khác sẽ nghĩ gì về tôi nếu tôi làm vậy', '4'),
            ('Tôi không đủ khả năng chi trả tiền bạc', '5'),
            ('Tôi đã thử yêu cầu nhưng không nhận được sự giúp đỡ', '6'),
            ('Tôi đã nhận được sự giúp đỡ từ nguồn khác', '7')
        ],
        'next': 'END'
    },
    'B18': {
        'q': 'Tôi hiểu bạn đã gặp vấn đề với tình trạng sức khỏe tâm thần của bản thân, nhưng bạn đã không đề cập đến việc nằm viện hoặc nhận sự giúp đỡ từ bất kỳ chuyên gia y tế nào. Liệu có bất kỳ hình thức giúp đỡ nào mà bạn nghĩ rằng mình cần trong 12 tháng qua nhưng lại không nhận được hay không?',
        'type': 'radio',
        'opts': [('Không', '1'), ('Có', '5')],
        'next': None
    },
    'B18_info': {
        'q': 'Bạn có nghĩ rằng bạn cần các thông tin về bệnh tâm thần, phương pháp điều trị và các dịch vụ hiện hành có sẵn không?',
        'type': 'radio',
        'opts': [('Không', '1'), ('Có', '5')],
        'next': None
    },
    'B18_info_a': {
        'q': 'Tại sao bạn không nhận sự giúp đỡ này? Vui lòng chọn lý do chính, hoặc một lý do phù hợp nhất với bạn.',
        'type': 'radio',
        'opts': [
            ('Tôi muốn tự mình xoay xở', '1'),
            ('Tôi không nghĩ có bất cứ điều gì có thể giúp ích cho bản thân', '2'),
            ('Tôi không biết nhận sự giúp đỡ ở đâu', '3'),
            ('Tôi e ngại trong việc yêu cầu giúp đỡ, hoặc lo sợ việc người khác sẽ nghĩ gì về tôi nếu tôi làm vậy', '4'),
            ('Tôi không đủ khả năng chi trả tiền bạc', '5'),
            ('Tôi đã thử yêu cầu nhưng không nhận được sự giúp đỡ', '6'),
            ('Tôi đã nhận được sự giúp đỡ từ nguồn khác', '7')
        ],
        'next': 'B19'
    },
    'B19': {
        'q': 'Bạn có nghĩ rằng bạn cần thuốc hoặc viên uống dạng nén không?',
        'type': 'radio',
        'opts': [('Không', '1'), ('Có', '5')],
        'next': None
    },
    'B19_a': {
        'q': 'Tại sao bạn không nhận sự giúp đỡ này? Vui lòng chọn lý do chính, hoặc một lý do phù hợp nhất với bạn.',
        'type': 'radio',
        'opts': [
            ('Tôi muốn tự mình xoay xở', '1'),
            ('Tôi không nghĩ có bất cứ điều gì có thể giúp ích cho bản thân', '2'),
            ('Tôi không biết nhận sự giúp đỡ ở đâu', '3'),
            ('Tôi e ngại trong việc yêu cầu giúp đỡ, hoặc lo sợ việc người khác sẽ nghĩ gì về tôi nếu tôi làm vậy', '4'),
            ('Tôi không đủ khả năng chi trả tiền bạc', '5'),
            ('Tôi đã thử yêu cầu nhưng không nhận được sự giúp đỡ', '6'),
            ('Tôi đã nhận được sự giúp đỡ từ nguồn khác', '7')
        ],
        'next': 'B20'
    },
    'B20': {
        'q': 'Bạn có nghĩ rằng bạn cần tham vấn hoặc liệu pháp trò chuyện không?',
        'type': 'radio',
        'opts': [('Không', '1'), ('Có', '5')],
        'next': None
    },
    'B20_a': {
        'q': 'Tại sao bạn không nhận sự giúp đỡ này? Vui lòng chọn lý do chính, hoặc một lý do phù hợp nhất với bạn.',
        'type': 'radio',
        'opts': [
            ('Tôi muốn tự mình xoay xở', '1'),
            ('Tôi không nghĩ có bất cứ điều gì có thể giúp ích cho bản thân', '2'),
            ('Tôi không biết nhận sự giúp đỡ ở đâu', '3'),
            ('Tôi e ngại trong việc yêu cầu giúp đỡ, hoặc lo sợ việc người khác sẽ nghĩ gì về tôi nếu tôi làm vậy', '4'),
            ('Tôi không đủ khả năng chi trả tiền bạc', '5'),
            ('Tôi đã thử yêu cầu nhưng không nhận được sự giúp đỡ', '6'),
            ('Tôi đã nhận được sự giúp đỡ từ nguồn khác', '7')
        ],
        'next': 'B21'
    },
    'B21': {
        'q': 'Bạn có nghĩ rằng bạn cần giúp đỡ để giải quyết các vấn đề thực tế như nhà ở hoặc tiền bạc không?',
        'type': 'radio',
        'opts': [('Không', '1'), ('Có', '5')],
        'next': None
    },
    'B21_a': {
        'q': 'Tại sao bạn không nhận sự giúp đỡ này? Vui lòng chọn lý do chính, hoặc một lý do phù hợp nhất với bạn.',
        'type': 'radio',
        'opts': [
            ('Tôi muốn tự mình xoay xở', '1'),
            ('Tôi không nghĩ có bất cứ điều gì có thể giúp ích cho bản thân', '2'),
            ('Tôi không biết nhận sự giúp đỡ ở đâu', '3'),
            ('Tôi e ngại trong việc yêu cầu giúp đỡ, hoặc lo sợ việc người khác sẽ nghĩ gì về tôi nếu tôi làm vậy', '4'),
            ('Tôi không đủ khả năng chi trả tiền bạc', '5'),
            ('Tôi đã thử yêu cầu nhưng không nhận được sự giúp đỡ', '6'),
            ('Tôi đã nhận được sự giúp đỡ từ nguồn khác', '7')
        ],
        'next': 'B22'
    },
    'B22': {
        'q': 'Bạn có nghĩ rằng bạn cần giúp đỡ để cải thiện khả năng làm việc, tự chăm sóc bản thân hoặc sử dụng thời gian không?',
        'type': 'radio',
        'opts': [('Không', '1'), ('Có', '5')],
        'next': None
    },
    'B22_a': {
        'q': 'Tại sao bạn không nhận sự giúp đỡ này? Vui lòng chọn lý do chính, hoặc một lý do phù hợp nhất với bạn.',
        'type': 'radio',
        'opts': [
            ('Tôi muốn tự mình xoay xở', '1'),
            ('Tôi không nghĩ có bất cứ điều gì có thể giúp ích cho bản thân', '2'),
            ('Tôi không biết nhận sự giúp đỡ ở đâu', '3'),
            ('Tôi e ngại trong việc yêu cầu giúp đỡ, hoặc lo sợ việc người khác sẽ nghĩ gì về tôi nếu tôi làm vậy', '4'),
            ('Tôi không đủ khả năng chi trả tiền bạc', '5'),
            ('Tôi đã thử yêu cầu nhưng không nhận được sự giúp đỡ', '6'),
            ('Tôi đã nhận được sự giúp đỡ từ nguồn khác', '7')
        ],
        'next': 'B23'
    },
    'B23': {
        'q': 'Cụ thể bạn có nghĩ rằng bạn cần sự giúp đỡ để cải thiện khả năng làm việc, hoặc sử dụng thời gian của bạn theo những cách khác nhau không?',
        'type': 'radio',
        'opts': [('Không', '1'), ('Có', '5')],
        'next': None
    },
    'B23_a': {
        'q': 'Tại sao bạn không nhận sự giúp đỡ này? Vui lòng chọn lý do chính, hoặc một lý do phù hợp nhất với bạn.',
        'type': 'radio',
        'opts': [
            ('Tôi muốn tự mình xoay xở', '1'),
            ('Tôi không nghĩ có bất cứ điều gì có thể giúp ích cho bản thân', '2'),
            ('Tôi không biết nhận sự giúp đỡ ở đâu', '3'),
            ('Tôi e ngại trong việc yêu cầu giúp đỡ, hoặc lo sợ việc người khác sẽ nghĩ gì về tôi nếu tôi làm vậy', '4'),
            ('Tôi không đủ khả năng chi trả tiền bạc', '5'),
            ('Tôi đã thử yêu cầu nhưng không nhận được sự giúp đỡ', '6'),
            ('Tôi đã nhận được sự giúp đỡ từ nguồn khác', '7')
        ],
        'next': 'B24'
    },
    'B24': {
        'q': 'Cụ thể bạn có nghĩ rằng bạn cần sự giúp đỡ để cải thiện khả năng tự chăm sóc bản thân hoặc nhà cửa của bản thân không?',
        'type': 'radio',
        'opts': [('Không', '1'), ('Có', '5')],
        'next': None
    },
    'B24_a': {
        'q': 'Tại sao bạn không nhận sự giúp đỡ này? Vui lòng chọn lý do chính, hoặc một lý do phù hợp nhất với bạn.',
        'type': 'radio',
        'opts': [
            ('Tôi muốn tự mình xoay xở', '1'),
            ('Tôi không nghĩ có bất cứ điều gì có thể giúp ích cho bản thân', '2'),
            ('Tôi không biết nhận sự giúp đỡ ở đâu', '3'),
            ('Tôi e ngại trong việc yêu cầu giúp đỡ, hoặc lo sợ việc người khác sẽ nghĩ gì về tôi nếu tôi làm vậy', '4'),
            ('Tôi không đủ khả năng chi trả tiền bạc', '5'),
            ('Tôi đã thử yêu cầu nhưng không nhận được sự giúp đỡ', '6'),
            ('Tôi đã nhận được sự giúp đỡ từ nguồn khác', '7')
        ],
        'next': 'B25'
    },
    'B25': {
        'q': 'Bạn có nghĩ rằng bạn cần sự giúp đỡ để gặp gỡ kết nối với mọi người để được hỗ trợ và có người đồng hành không?',
        'type': 'radio',
        'opts': [('Không', '1'), ('Có', '5')],
        'next': None
    },
    'B25_a': {
        'q': 'Tại sao bạn không nhận sự giúp đỡ này? Vui lòng chọn lý do chính, hoặc một lý do phù hợp nhất với bạn.',
        'type': 'radio',
        'opts': [
            ('Tôi muốn tự mình xoay xở', '1'),
            ('Tôi không nghĩ có bất cứ điều gì có thể giúp ích cho bản thân', '2'),
            ('Tôi không biết nhận sự giúp đỡ ở đâu', '3'),
            ('Tôi e ngại trong việc yêu cầu giúp đỡ, hoặc lo sợ việc người khác sẽ nghĩ gì về tôi nếu tôi làm vậy', '4'),
            ('Tôi không đủ khả năng chi trả tiền bạc', '5'),
            ('Tôi đã thử yêu cầu nhưng không nhận được sự giúp đỡ', '6'),
            ('Tôi đã nhận được sự giúp đỡ từ nguồn khác', '7')
        ],
        'next': 'END'
    }
}

def render_question(q_id, config):
    """Hiển thị câu hỏi"""
    
    # Xử lý B9 - câu hỏi động
    if q_id == 'B9':
        B7 = st.session_state.answers.get('B7', 0)
        B2b = st.session_state.answers.get('B2b', '1')
        B3 = st.session_state.answers.get('B3', '1')
        B4 = st.session_state.answers.get('B4', '1')
        
        # Xác định loại giúp đỡ
        has_mental_hospitalization = B2b == '5' or B3 == '5' or B4 == '5'
        has_consultation = B7 and int(B7) >= 1
        
        if has_consultation and has_mental_hospitalization:
            help_type = "các cuộc tư vấn và lần nhập viện"
        elif has_consultation and not has_mental_hospitalization:
            help_type = "các cuộc tư vấn"
        elif not has_consultation and has_mental_hospitalization:
            help_type = "các lần nhập viện"
        else:
            help_type = "các cuộc tư vấn hoặc lần nhập viện"
        
        question_text = f"Hãy nhìn vào các hình thức giúp đỡ dưới đây. Bạn đã nhận được hình thức giúp đỡ nào trong {help_type}, cho bất kỳ vấn đề nào liên quan đến sức khỏe tâm thần của bạn? (Chọn tất cả những hình thức phù hợp)"
        st.markdown(f'### {question_text}')
    else:
        st.markdown(f'### {config["q"]}')
    
    if 'note' in config:
        st.info(config['note'])
    
    qtype = config['type']
    
    if qtype == 'info':
        st.success("ℹ️ " + config['q'])
        st.session_state.answers[q_id] = 'info'
        return True
    
    elif qtype == 'radio':
        opts_labels = [o[0] for o in config['opts']]
        selected = st.radio("Chọn câu trả lời:", opts_labels, key=f"q_{q_id}", index=None)
        
        if selected:
            for label, val in config['opts']:
                if label == selected:
                    st.session_state.answers[q_id] = val
                    return True
        return False
    
    elif qtype == 'checkbox':
        st.write("Chọn tất cả đáp án phù hợp:")
        selected_vals = []
        for label, val in config['opts']:
            if st.checkbox(label, key=f"cb_{q_id}_{val}"):
                selected_vals.append(val)
        
        if selected_vals:
            st.session_state.answers[q_id] = selected_vals
            return True
        return False
    
    elif qtype == 'textarea':
        answer = st.text_area("Nhập câu trả lời:", key=f"ta_{q_id}", height=150)
        if answer.strip():
            st.session_state.answers[q_id] = answer
            return True
        return False
    
    elif qtype == 'number':
        answer = st.number_input("Nhập số:", min_value=0, step=1, key=f"num_{q_id}")
        st.session_state.answers[q_id] = answer
        return True
    
    return False

def get_next_question(current_q, answers):
    """Xác định câu hỏi tiếp theo"""
    config = SURVEY_CONFIG.get(current_q, {})
    
    # Ưu tiên logic function
    if 'next_logic' in config:
        answer = answers.get(current_q)
        return config['next_logic'](answer)
    
    # Logic phức tạp từ hàm riêng
    next_q = get_next_question_logic(current_q, answers)
    if next_q:
        return next_q
    
    # Next đơn giản
    if 'next' in config:
        return config['next']
    
    return 'END'

def main():
    st.title("🏥 Bảng hỏi Sức khỏe Tâm thần")
    st.markdown("---")
    
    # Nhập tên người trả lời ở đầu
    if not st.session_state.respondent_name:
        st.markdown("### 👤 Trước tiên, vui lòng nhập tên của bạn")
        respondent_name = st.text_input("Tên của bạn:")
        
        if respondent_name.strip():
            st.session_state.respondent_name = respondent_name
            st.success(f"✅ Xin chào {respondent_name}! Hãy bắt đầu trả lời bảng hỏi.")
            st.rerun()
        else:
            st.warning("⚠️ Vui lòng nhập tên trước khi tiếp tục")
            st.stop()
    
    if not st.session_state.completed:
        current_q = st.session_state.current_question
        
        if current_q == 'END':
            st.session_state.completed = True
            st.rerun()
        
        # Progress
        total_qs = len(SURVEY_CONFIG)
        current_pos = len(st.session_state.history)
        progress = min(current_pos / total_qs, 1.0)
        
        st.progress(progress)
        st.markdown(f'<p class="progress-text">Câu {current_pos} / ~{total_qs}</p>', unsafe_allow_html=True)
        
        # Render
        config = SURVEY_CONFIG.get(current_q)
        if not config:
            st.error(f"Câu hỏi {current_q} không tồn tại")
            return
        
        st.markdown('<div class="question-box">', unsafe_allow_html=True)
        has_answer = render_question(current_q, config)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Navigation
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            if len(st.session_state.history) > 1:
                if st.button("⬅️ Quay lại", use_container_width=True):
                    st.session_state.history.pop()
                    st.session_state.current_question = st.session_state.history[-1]
                    st.rerun()
        
        with col3:
            if st.button("Tiếp theo ➡️", use_container_width=True, disabled=not has_answer):
                next_q = get_next_question(current_q, st.session_state.answers)
                
                if next_q == 'END' or not next_q:
                    st.session_state.completed = True
                    st.rerun()
                else:
                    st.session_state.current_question = next_q
                    st.session_state.history.append(next_q)
                    st.rerun()
    
    else:
        # Hoàn thành
        st.success("✅ Cảm ơn bạn đã hoàn thành bảng hỏi!")
        st.balloons()
        
        st.markdown(f"### 👤 Người trả lời: **{st.session_state.respondent_name}**")
        st.markdown("### 📊 Tóm tắt câu trả lời")
        
        for q_id, answer in st.session_state.answers.items():
            if q_id in SURVEY_CONFIG:
                config = SURVEY_CONFIG[q_id]
                with st.expander(f"**{q_id}**: {config['q'][:60]}..."):
                    st.write(f"**Câu hỏi:** {config['q']}")
                    
                    if isinstance(answer, list):
                        answer_text = []
                        for val in answer:
                            for label, v in config.get('opts', []):
                                if v == val:
                                    answer_text.append(label)
                                    break
                        st.write(f"**Trả lời:** {', '.join(answer_text)}")
                    elif config['type'] == 'radio' and 'opts' in config:
                        for label, val in config['opts']:
                            if val == answer:
                                st.write(f"**Trả lời:** {label}")
                                break
                    else:
                        st.write(f"**Trả lời:** {answer}")
        
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            json_data = json.dumps(st.session_state.answers, ensure_ascii=False, indent=2)
            st.download_button(
                "📥 Tải xuống (JSON)",
                json_data,
                f"mental_health_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                "application/json"
            )
        
        with col2:
            # Gửi khảo sát lên Drive
            if st.button("📤 Gửi khảo sát", use_container_width=True):
                upload_to_google_drive(st.session_state.respondent_name, st.session_state.answers)
        
        with col3:
            if st.button("🔄 Làm lại", use_container_width=True):
                st.session_state.current_question = 'A1'
                st.session_state.answers = {}
                st.session_state.history = ['A1']
                st.session_state.completed = False
                st.session_state.respondent_name = ""
                st.rerun()

if __name__ == "__main__":
    main()
