import streamlit as st
import json
from datetime import datetime

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

# Cấu hình bảng hỏi - mapping từ document
SURVEY_CONFIG = {
    'A1': {
        'question': 'ANH/CHỊ CÓ PHẢI LÀ THÂN CHỦ HOẶC BỆNH NHÂN ĐÃ CÓ HIỂU BIẾT VỀ CÁC DỊCH VỤ SỨC KHỎE TÂM THẦN KHÔNG?',
        'type': 'radio',
        'options': [
            {'label': 'Có', 'value': '5', 'next': 'A2'},
            {'label': 'Không', 'value': '1', 'next': 'A2'}
        ]
    },
    'A2': {
        'question': 'Hãy nghĩ lại trong năm vừa rồi, và xem xét liệu bạn có gặp bất cứ khó khăn nào liên quan đến vấn đề sức khỏe tâm thần của mình trong thời gian đó không: Bạn có nghĩ rằng, trong năm vừa rồi, bạn đã có bất cứ lúc nào gặp phải các vấn đề với sức khỏe tâm thần của bản thân không?',
        'type': 'radio',
        'options': [
            {'label': 'Có', 'value': '5', 'next': 'A3'},
            {'label': 'Không', 'value': '1', 'next': 'B1'}
        ]
    },
    'A3': {
        'question': 'Bạn sẽ gọi vấn đề hoặc những vấn đề mà bạn gặp phải liên quan đến sức khỏe tâm thần của mình là gì?',
        'type': 'textarea',
        'next': 'B1',
        'note': '(THĂM DÒ NẾU CẦN THIẾT. THÔNG TIN CÓ THỂ ĐƯỢC THÊM VÀO ĐÂY TỪ CÁC CÂU TRẢ LỜI TRƯỚC ĐÓ TRONG CUỘC PHỎNG VẤN)'
    },
    'B1': {
        'question': 'Trong 12 tháng qua bạn đã bao giờ từng nhập viện ít nhất là một đêm tại bất kỳ bệnh viện nào không?',
        'type': 'radio',
        'options': [
            {'label': 'Có', 'value': '5', 'next': 'B2'},
            {'label': 'Không', 'value': '1', 'next': 'B5'}
        ]
    },
    'B2': {
        'question': 'Bạn đã bao giờ từng nhập viện qua đêm tại một bệnh viện đa khoa không?',
        'type': 'radio',
        'options': [
            {'label': 'Có', 'value': '5', 'next': 'B2a'},
            {'label': 'Không', 'value': '1', 'next': 'B3'}
        ]
    },
    'B2a': {
        'question': 'Việc bạn nhập viện đó có phải là do bệnh lý về thể chất hay không?',
        'type': 'radio',
        'options': [
            {'label': 'Có', 'value': '5', 'next': 'B2a1'},
            {'label': 'Không', 'value': '1', 'next': 'B2b'}
        ]
    },
    'B2a1': {
        'question': 'Trong 12 tháng vừa rồi, đã có bao nhiêu lần bạn nhập viện ít nhất một đêm tại bệnh viện đa khoa do bệnh lý về thể chất?',
        'type': 'number',
        'next': 'B2a2'
    },
    'B2a2': {
        'question': 'Tổng cộng bạn đã ở lại bao nhiêu đêm tại bệnh viện đa khoa do bệnh lý về thể chất?',
        'type': 'number',
        'next': 'B2b'
    },
    'B2b': {
        'question': 'Bạn đã bao giờ từng nhập viện qua đêm tại một bệnh viện đa khoa do các vấn đề thần kinh hoặc tâm thần gây ra trong vòng 12 tháng qua không?',
        'type': 'radio',
        'options': [
            {'label': 'Có', 'value': '5', 'next': 'B2b1'},
            {'label': 'Không', 'value': '1', 'next': 'B3'}
        ]
    },
    'B2b1': {
        'question': 'Trong vòng 12 tháng qua, đã có bao nhiêu lần bạn từng nhập viện ít nhất một đêm tại bệnh viện đa khoa do các vấn đề thần kinh hoặc tâm thần gây ra?',
        'type': 'number',
        'next': 'B2b2'
    },
    'B2b2': {
        'question': 'Tổng cộng bạn đã ở lại bao nhiêu đêm tại bệnh viện đa khoa vì ảnh hưởng của các vấn đề thần kinh hoặc tâm thần?',
        'type': 'number',
        'next': 'B2b3'
    },
    'B2b3': {
        'question': 'Bạn đã nằm giường hạng dịch vụ hay phổ thông?',
        'type': 'radio',
        'options': [
            {'label': 'Dịch vụ (tư nhân)', 'value': 'private', 'next': 'B3'},
            {'label': 'Phổ thông (công)', 'value': 'public', 'next': 'B3'}
        ]
    },
    'B3': {
        'question': 'Trong 12 tháng vừa rồi bạn đã từng nhập viện qua đêm tại một bệnh viện tâm thần không?',
        'type': 'radio',
        'options': [
            {'label': 'Có', 'value': '5', 'next': 'B3a1'},
            {'label': 'Không', 'value': '1', 'next': 'B4'}
        ]
    },
    'B3a1': {
        'question': 'Trong vòng 12 tháng qua, đã bao nhiêu lần bạn nhập viện ít nhất một đêm tại bệnh viện tâm thần?',
        'type': 'number',
        'next': 'B3a2'
    },
    'B3a2': {
        'question': 'Tổng cộng bạn đã ở lại bao nhiêu đêm tại bệnh viện tâm thần?',
        'type': 'number',
        'next': 'B3a3'
    },
    'B3a3': {
        'question': 'Đó là bệnh viện tâm thần thuộc tư nhân hay Nhà Nước?',
        'type': 'radio',
        'options': [
            {'label': 'Tư nhân', 'value': 'private', 'next': 'B4'},
            {'label': 'Nhà Nước', 'value': 'public', 'next': 'B4'}
        ]
    },
    'B4': {
        'question': 'Trong 12 tháng vừa rồi bạn đã từng nhập viện qua đêm tại bất kỳ đơn vị cai nghiện ma túy và rượu bia nào ở bệnh viện không?',
        'type': 'radio',
        'options': [
            {'label': 'Có', 'value': '5', 'next': 'B4a1'},
            {'label': 'Không', 'value': '1', 'next': 'B5'}
        ]
    },
    'B4a1': {
        'question': 'Trong vòng 12 tháng qua, đã có bao nhiêu lần bạn nhập viện ít nhất một đêm tại các đơn vị cai nghiện ma túy và rượu bia?',
        'type': 'number',
        'next': 'B4a2'
    },
    'B4a2': {
        'question': 'Tổng cộng bạn đã ở lại bao nhiêu đêm tại các đơn vị cai nghiện ma túy và rượu bia?',
        'type': 'number',
        'next': 'B4a3'
    },
    'B4a3': {
        'question': 'Đó là đơn vị thuộc tư nhân hay Nhà Nước?',
        'type': 'radio',
        'options': [
            {'label': 'Tư nhân', 'value': 'private', 'next': 'B5'},
            {'label': 'Nhà Nước', 'value': 'public', 'next': 'B5'}
        ]
    },
    'B5': {
        'question': 'Trong 12 tháng qua, (ngoài thời gian bạn đã ở bệnh viện), bạn có gặp bất kỳ bác sĩ hoặc chuyên gia y tế nào liên quan đến tình trạng sức khỏe của chính bạn không?',
        'type': 'radio',
        'note': 'Các chuyên gia y tế bao gồm: Bác sĩ đa khoa, Bác sĩ chuyên khoa, Bác sĩ tâm thần, Nhà tâm lý học, Nhân viên công tác xã hội, Tư vấn viên, Điều dưỡng/Y tá, v.v.',
        'options': [
            {'label': 'Có', 'value': '5', 'next': 'B5a'},
            {'label': 'Không', 'value': '1', 'next': 'B18'}
        ]
    },
    'B5a': {
        'question': 'Bạn đã gặp những chuyên gia y tế nào? (Chọn tất cả các đáp án phù hợp)',
        'type': 'checkbox',
        'options': [
            {'label': 'Bác sĩ đa khoa', 'value': 'gp'},
            {'label': 'Bác sĩ chẩn đoán hình ảnh hoặc chuyên khoa X-quang', 'value': 'radiologist'},
            {'label': 'Bác sĩ bệnh lý học hoặc chuyên khoa xét nghiệm máu', 'value': 'pathologist'},
            {'label': 'Bác sĩ nội khoa hoặc chuyên viên y tế khác', 'value': 'physician'},
            {'label': 'Bác sĩ phẫu thuật hoặc bác sĩ phụ khoa', 'value': 'surgeon'},
            {'label': 'Bác sĩ tâm thần', 'value': 'psychiatrist'},
            {'label': 'Nhà tâm lý học', 'value': 'psychologist'},
            {'label': 'Nhân viên công tác xã hội hoặc cán bộ phúc lợi', 'value': 'social_worker'},
            {'label': 'Tư vấn viên về tình trạng nghiện chất', 'value': 'drug_counsellor'},
            {'label': 'Các tư vấn viên khác', 'value': 'other_counsellor'},
            {'label': 'Điều dưỡng/Y tá', 'value': 'nurse'},
            {'label': 'Nhóm chuyên gia sức khỏe tâm thần', 'value': 'mental_health_team'},
            {'label': 'Dược sĩ tư vấn chuyên môn', 'value': 'pharmacist'},
            {'label': 'Nhân viên xe cứu thương', 'value': 'ambulance'},
            {'label': 'Các chuyên gia y tế khác', 'value': 'other'}
        ],
        'next': 'B6_check'
    },
    'B6_check': {
        'question': 'Tiếp theo chúng tôi sẽ hỏi chi tiết về các lần tham vấn với chuyên gia y tế',
        'type': 'info',
        'next': 'B9'
    },
    'B9': {
        'question': 'Bạn đã nhận được hình thức giúp đỡ nào trong số này từ các cuộc tham vấn hoặc lần nhập viện, cho bất kỳ vấn đề nào liên quan đến sức khỏe tâm thần của bạn? (Chọn tất cả các đáp án phù hợp)',
        'type': 'checkbox',
        'options': [
            {'label': 'Thông tin về bệnh tâm thần, các phương pháp điều trị và các dịch vụ hiện hành có sẵn', 'value': 'info'},
            {'label': 'Thuốc hoặc viên uống dạng nén', 'value': 'medicine'},
            {'label': 'Tâm lý trị liệu - thảo luận về các vấn đề nguyên nhân bắt nguồn từ quá khứ của bạn', 'value': 'psychotherapy'},
            {'label': 'Liệu pháp nhận thức hành vi - học cách để thay đổi suy nghĩ, hành vi và cảm xúc của bạn', 'value': 'cbt'},
            {'label': 'Tham vấn - giúp nói chuyện để giải quyết các vấn đề của bạn', 'value': 'counselling'},
            {'label': 'Giúp giải quyết các vấn đề thực tế, chẳng hạn như nhà ở hoặc tiền bạc', 'value': 'practical'},
            {'label': 'Giúp cải thiện khả năng làm việc, hoặc sử dụng thời gian hiệu quả hơn', 'value': 'work'},
            {'label': 'Giúp bạn cải thiện khả năng tự chăm sóc bản thân hoặc nhà cửa', 'value': 'selfcare'},
            {'label': 'Giúp bạn gặp gỡ kết nối với mọi người để được hỗ trợ và có người đồng hành', 'value': 'social'},
            {'label': 'Khác', 'value': 'other'}
        ],
        'next': 'B10_check'
    },
    'B10_check': {
        'question': 'Tiếp theo chúng tôi sẽ hỏi về mức độ đầy đủ của các hình thức giúp đỡ bạn đã nhận',
        'type': 'info',
        'next': 'END'
    },
    'B18': {
        'question': 'Tôi hiểu bạn đã gặp vấn đề với tình trạng sức khỏe tâm thần của bản thân nhưng bạn đã không đề cập đến việc nằm viện hoặc nhận sự giúp đỡ từ bất kỳ chuyên gia y tế nào. Liệu có bất kỳ hình thức giúp đỡ nào mà bạn nghĩ rằng mình cần trong 12 tháng qua nhưng lại không nhận được hay không?',
        'type': 'radio',
        'options': [
            {'label': 'Có', 'value': '5', 'next': 'B18a'},
            {'label': 'Không', 'value': '1', 'next': 'END'}
        ]
    },
    'B18a': {
        'question': 'Bạn có nghĩ rằng bạn cần các thông tin về bệnh tâm thần, phương pháp điều trị và các dịch vụ hiện hành có sẵn không?',
        'type': 'radio',
        'options': [
            {'label': 'Có', 'value': '5', 'next': 'B18a_reason'},
            {'label': 'Không', 'value': '1', 'next': 'B19'}
        ]
    },
    'B18a_reason': {
        'question': 'Tại sao bạn không nhận sự giúp đỡ này? Vui lòng chọn lý do chính',
        'type': 'radio',
        'options': [
            {'label': 'Tôi muốn tự mình xoay xở', 'value': '1'},
            {'label': 'Tôi không nghĩ có bất cứ điều gì có thể giúp ích cho bản thân', 'value': '2'},
            {'label': 'Tôi không biết nhận sự giúp đỡ ở đâu', 'value': '3'},
            {'label': 'Tôi e ngại trong việc yêu cầu giúp đỡ, hoặc lo sợ người khác nghĩ gì về tôi', 'value': '4'},
            {'label': 'Tôi không đủ khả năng chi trả tiền bạc', 'value': '5'},
            {'label': 'Tôi đã thử yêu cầu nhưng không nhận được sự giúp đỡ', 'value': '6'},
            {'label': 'Tôi đã nhận được sự giúp đỡ từ nguồn khác', 'value': '7'}
        ],
        'next': 'B19'
    },
    'B19': {
        'question': 'Bạn có nghĩ rằng bạn cần thuốc hoặc viên uống dạng nén không?',
        'type': 'radio',
        'options': [
            {'label': 'Có', 'value': '5', 'next': 'B19_reason'},
            {'label': 'Không', 'value': '1', 'next': 'B20'}
        ]
    },
    'B19_reason': {
        'question': 'Tại sao bạn không nhận sự giúp đỡ này? Vui lòng chọn lý do chính',
        'type': 'radio',
        'options': [
            {'label': 'Tôi muốn tự mình xoay xở', 'value': '1'},
            {'label': 'Tôi không nghĩ có bất cứ điều gì có thể giúp ích cho bản thân', 'value': '2'},
            {'label': 'Tôi không biết nhận sự giúp đỡ ở đâu', 'value': '3'},
            {'label': 'Tôi e ngại trong việc yêu cầu giúp đỡ, hoặc lo sợ người khác nghĩ gì về tôi', 'value': '4'},
            {'label': 'Tôi không đủ khả năng chi trả tiền bạc', 'value': '5'},
            {'label': 'Tôi đã thử yêu cầu nhưng không nhận được sự giúp đỡ', 'value': '6'},
            {'label': 'Tôi đã nhận được sự giúp đỡ từ nguồn khác', 'value': '7'}
        ],
        'next': 'B20'
    },
    'B20': {
        'question': 'Bạn có nghĩ rằng bạn cần tham vấn hoặc liệu pháp trò chuyện không?',
        'type': 'radio',
        'options': [
            {'label': 'Có', 'value': '5', 'next': 'B20_reason'},
            {'label': 'Không', 'value': '1', 'next': 'END'}
        ]
    },
    'B20_reason': {
        'question': 'Tại sao bạn không nhận sự giúp đỡ này? Vui lòng chọn lý do chính',
        'type': 'radio',
        'options': [
            {'label': 'Tôi muốn tự mình xoay xở', 'value': '1'},
            {'label': 'Tôi không nghĩ có bất cứ điều gì có thể giúp ích cho bản thân', 'value': '2'},
            {'label': 'Tôi không biết nhận sự giúp đỡ ở đâu', 'value': '3'},
            {'label': 'Tôi e ngại trong việc yêu cầu giúp đỡ, hoặc lo sợ người khác nghĩ gì về tôi', 'value': '4'},
            {'label': 'Tôi không đủ khả năng chi trả tiền bạc', 'value': '5'},
            {'label': 'Tôi đã thử yêu cầu nhưng không nhận được sự giúp đỡ', 'value': '6'},
            {'label': 'Tôi đã nhận được sự giúp đỡ từ nguồn khác', 'value': '7'}
        ],
        'next': 'END'
    }
}

def get_next_question(current_q, answer):
    """Xác định câu hỏi tiếp theo dựa vào logic"""
    config = SURVEY_CONFIG[current_q]
    
    # Nếu là checkbox hoặc textarea, lấy next trực tiếp
    if config['type'] in ['checkbox', 'textarea', 'number', 'info']:
        return config.get('next', 'END')
    
    # Nếu là radio, tìm option được chọn
    if config['type'] == 'radio':
        for opt in config['options']:
            if opt['value'] == answer:
                return opt.get('next', 'END')
    
    return 'END'

def render_question(q_id):
    """Hiển thị câu hỏi"""
    if q_id == 'END':
        st.session_state.completed = True
        return
    
    config = SURVEY_CONFIG[q_id]
    
    st.markdown(f'<div class="question-box">', unsafe_allow_html=True)
    st.markdown(f"### Câu hỏi: {config['question']}")
    
    if 'note' in config:
        st.info(config['note'])
    
    # Render theo loại câu hỏi
    if config['type'] == 'radio':
        options = [opt['label'] for opt in config['options']]
        selected = st.radio(
            "Chọn câu trả lời:",
            options,
            key=f"q_{q_id}",
            index=None
        )
        
        if selected:
            # Tìm value tương ứng
            for opt in config['options']:
                if opt['label'] == selected:
                    st.session_state.answers[q_id] = opt['value']
                    break
    
    elif config['type'] == 'checkbox':
        st.write("Chọn tất cả các đáp án phù hợp:")
        selected_values = []
        for opt in config['options']:
            if st.checkbox(opt['label'], key=f"q_{q_id}_{opt['value']}"):
                selected_values.append(opt['value'])
        
        if selected_values:
            st.session_state.answers[q_id] = selected_values
    
    elif config['type'] == 'textarea':
        answer = st.text_area(
            "Nhập câu trả lời của bạn:",
            key=f"q_{q_id}",
            height=150
        )
        if answer:
            st.session_state.answers[q_id] = answer
    
    elif config['type'] == 'number':
        answer = st.number_input(
            "Nhập số:",
            min_value=0,
            step=1,
            key=f"q_{q_id}"
        )
        st.session_state.answers[q_id] = answer
    
    elif config['type'] == 'info':
        st.info("📋 " + config['question'])
        st.session_state.answers[q_id] = 'acknowledged'
    
    st.markdown('</div>', unsafe_allow_html=True)

def main():
    st.title("🏥 Bảng hỏi Sức khỏe Tâm thần")
    st.markdown("---")
    
    if not st.session_state.completed:
        # Hiển thị tiến độ
        total_questions = len(SURVEY_CONFIG)
        current_position = len(st.session_state.history)
        progress = min(current_position / total_questions, 1.0)
        
        st.progress(progress)
        st.markdown(f'<p class="progress-text">Câu hỏi {current_position} / {total_questions}</p>', 
                   unsafe_allow_html=True)
        
        # Hiển thị câu hỏi hiện tại
        current_q = st.session_state.current_question
        render_question(current_q)
        
        # Nút điều hướng
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            if len(st.session_state.history) > 1:
                if st.button("⬅️ Quay lại", use_container_width=True):
                    st.session_state.history.pop()
                    st.session_state.current_question = st.session_state.history[-1]
                    st.rerun()
        
        with col3:
            # Check nếu câu hỏi đã được trả lời
            can_proceed = current_q in st.session_state.answers
            
            if st.button("Tiếp theo ➡️", use_container_width=True, disabled=not can_proceed):
                answer = st.session_state.answers[current_q]
                next_q = get_next_question(current_q, answer)
                
                if next_q == 'END':
                    st.session_state.completed = True
                    st.rerun()
                else:
                    st.session_state.current_question = next_q
                    st.session_state.history.append(next_q)
                    st.rerun()
    
    else:
        # Trang hoàn thành
        st.success("✅ Cảm ơn bạn đã hoàn thành bảng hỏi!")
        st.balloons()
        
        st.markdown("### 📊 Tóm tắt câu trả lời của bạn")
        
        # Hiển thị tóm tắt
        for q_id, answer in st.session_state.answers.items():
            if q_id in SURVEY_CONFIG:
                config = SURVEY_CONFIG[q_id]
                with st.expander(f"**{q_id}**: {config['question'][:80]}..."):
                    st.write(f"**Câu hỏi:** {config['question']}")
                    
                    # Format câu trả lời
                    if isinstance(answer, list):
                        # Checkbox
                        answer_text = []
                        for val in answer:
                            for opt in config['options']:
                                if opt['value'] == val:
                                    answer_text.append(opt['label'])
                                    break
                        st.write(f"**Trả lời:** {', '.join(answer_text)}")
                    elif config['type'] == 'radio':
                        # Radio
                        for opt in config['options']:
                            if opt['value'] == answer:
                                st.write(f"**Trả lời:** {opt['label']}")
                                break
                    else:
                        st.write(f"**Trả lời:** {answer}")
        
        # Xuất dữ liệu
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            # Tải về JSON
            json_data = json.dumps(st.session_state.answers, ensure_ascii=False, indent=2)
            st.download_button(
                label="📥 Tải xuống dữ liệu (JSON)",
                data=json_data,
                file_name=f"mental_health_survey_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        
        with col2:
            if st.button("🔄 Làm lại bảng hỏi", use_container_width=True):
                st.session_state.current_question = 'A1'
                st.session_state.answers = {}
                st.session_state.history = ['A1']
                st.session_state.completed = False
                st.rerun()

if __name__ == "__main__":
    main()