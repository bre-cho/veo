export function generateAdsPlan(input: any) {
  return {
    objective: input.goal === "sale" ? "Sales / Conversions" : "Leads / Traffic",
    angles: [
      "Problem angle",
      "Result angle",
      "Offer angle"
    ],
    captions: [
      "Bạn đang mất khách vì visual chưa đủ rõ?",
      "Một poster tốt giúp khách hiểu sản phẩm nhanh hơn.",
      "Tạo bản demo cho sản phẩm của bạn ngay hôm nay."
    ],
    ctas: ["Xem ngay", "Nhận demo", "Đăng ký"],
    budgetTest: "300k/ngày trong 24h",
    kpi: ["CTR", "CPC", "CPM", "Lead", "CPL", "Close rate"]
  };
}
