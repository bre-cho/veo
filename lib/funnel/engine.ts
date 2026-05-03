export function generateFunnel(input: any) {
  const product = input.product || "sản phẩm";

  return {
    landing: {
      heroHeadline: `Tạo kết quả tốt hơn với ${product}`,
      subHeadline: "Hiểu nhanh, thấy rõ lợi ích, hành động ngay.",
      cta: input.goal === "sale" ? "Mua ngay" : "Nhận demo miễn phí"
    },
    sections: [
      "Problem",
      "Solution",
      "Demo / Visual proof",
      "Offer",
      "FAQ",
      "Lead form"
    ],
    thankYou: "Cảm ơn bạn. Chúng tôi sẽ gửi demo trong ít phút.",
    email: {
      subject: `Demo cho ${product}`,
      body: "Đây là demo bạn vừa yêu cầu. Nếu cần tối ưu thêm, hãy phản hồi email này."
    }
  };
}
