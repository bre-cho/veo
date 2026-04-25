/**
 * Vietnamese translation dictionary (primary language).
 */
const vi = {
  // Navigation
  nav_dashboard: "Bảng điều khiển",
  nav_script_upload: "Tải kịch bản",
  nav_render_jobs: "Hàng chờ render",
  nav_settings: "Cài đặt",
  nav_avatar_builder: "Xây dựng Avatar",
  nav_marketplace: "Chợ Avatar",
  nav_analytics: "Phân tích",
  nav_wallet: "Ví tiền",
  nav_creator: "Nhà sáng tác",
  nav_strategy: "Chiến lược",
  nav_templates: "Mẫu",
  nav_production_studio: "Studio sản xuất",
  nav_projects: "Dự án",
  nav_autopilot: "Tự động lái",
  nav_audio: "Âm thanh",
  nav_governance: "Quản trị",

  // Home page
  home_eyebrow: "Nhà máy render",
  home_title: "Nền tảng xuất bản video đa nhà cung cấp",
  home_description:
    "Hệ thống nội bộ để tải kịch bản, xây dựng kế hoạch nhà cung cấp, quản lý hàng chờ render, giám sát hoàn thành, lưu trữ đối tượng, bảng điều khiển và giao diện xem lại công việc.",
  home_card_dashboard: "Bảng điều khiển",
  home_card_dashboard_desc: "Tổng quan, tạo dự án và điểm vào không gian làm việc",
  home_card_script_upload: "Tải kịch bản",
  home_card_script_upload_desc: "Tải .txt/.docx → xem trước → chỉnh sửa → kiểm tra → tạo dự án",
  home_card_audio_studio: "Studio âm thanh",
  home_card_audio_studio_desc: "Hồ sơ giọng đọc, phát âm theo nhịp thở, nhạc nền và quy trình trộn âm",
  home_card_autopilot: "Tự động lái",
  home_card_autopilot_desc: "Khoá khẩn cấp, cổng phát hành, điều khiển thời gian thực và mặt phẳng thông báo",
  home_card_strategy: "Chiến lược",
  home_card_strategy_desc: "Tín hiệu chiến lược doanh nghiệp, chỉ thị, phân bổ danh mục và xem rủi ro SLA",
  home_card_templates: "Mẫu",
  home_card_templates_desc: "Thư viện mẫu, trích xuất, tái sử dụng, tạo hàng loạt và phân tích",
  home_card_projects: "Dự án",
  home_card_projects_desc: "Không gian làm việc dự án, điều khiển Veo 3.1, trạng thái render, render lại cảnh và xem trước đầu ra",
  home_card_governance: "Quản trị",
  home_card_governance_desc: "Lập lịch thực thi, cooldowns, điều khiển điều phối và đường dẫn thăng cấp chính sách",
  home_card_settings: "Cài đặt",
  home_card_settings_desc: "Quản lý tài khoản Google AI với xoay vòng tài khoản để chạy nhiều tài khoản đồng thời",
  home_card_api_docs: "Tài liệu API",

  // Dashboard / incidents
  dashboard_title: "Bảng điều khiển",
  dashboard_incidents: "Sự cố",
  dashboard_no_incidents: "Không có sự cố",
  dashboard_recent_events: "Sự kiện gần đây",

  // Realtime progress
  realtime_progress_title: "Tiến trình thời gian thực",
  realtime_no_events: "Chưa có sự kiện",

  // Rebuild decision panel
  rebuild_decision_title: "Quyết định rebuild",
  rebuild_strategy: "Chiến lược được chọn",
  rebuild_reason: "Lý do rebuild",
  rebuild_mandatory_scenes: "Cảnh bắt buộc",
  rebuild_optional_scenes: "Cảnh có thể bỏ qua",
  rebuild_skipped_scenes: "Cảnh bỏ qua",
  rebuild_estimated_cost: "Chi phí ước tính",
  rebuild_estimated_time: "Thời gian ước tính",
  rebuild_warnings: "Cảnh báo",
  rebuild_approve_btn: "Phê duyệt & thực thi",
  rebuild_cancel_btn: "Huỷ",
  rebuild_status_allow: "Cho phép",
  rebuild_status_downgrade: "Hạ cấp",
  rebuild_status_block: "Chặn",
  rebuild_no_decision: "Chưa có quyết định rebuild",
  rebuild_decision_loading: "Đang tính toán...",
  rebuild_budget_policy: "Chính sách ngân sách",

  // Budget policy selector
  budget_policy_cheap: "Tiết kiệm",
  budget_policy_balanced: "Cân bằng",
  budget_policy_quality: "Chất lượng cao",
  budget_policy_emergency: "Khẩn cấp",
  budget_policy_label: "Chính sách ngân sách",
  budget_policy_description_cheap: "Giới hạn chi phí thấp, cho phép hạ cấp",
  budget_policy_description_balanced: "Cân bằng giữa chi phí và chất lượng",
  budget_policy_description_quality: "Không hạ cấp, bao gồm cả cảnh tuỳ chọn",
  budget_policy_description_emergency: "Ngân sách tối thiểu, hạ cấp tích cực",

  // Common
  loading: "Đang tải...",
  error: "Lỗi",
  success: "Thành công",
  confirm: "Xác nhận",
  cancel: "Huỷ",
  save: "Lưu",
  close: "Đóng",
  back: "Quay lại",
  next: "Tiếp theo",
  scene: "Cảnh",
  scenes: "Cảnh",
  cost: "Chi phí",
  time: "Thời gian",
  status: "Trạng thái",
  actions: "Hành động",
} as const;

export type TranslationKey = keyof typeof vi;
export default vi;
