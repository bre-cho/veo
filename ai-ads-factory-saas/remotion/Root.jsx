import { Composition } from "remotion";
import { AdVideo } from "./AdVideo";

export function RemotionRoot() {
  return (
    <Composition
      id="AdVideo"
      component={AdVideo}
      durationInFrames={360}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={{
        hook: "Bạn đang đốt tiền ads?",
        headline: "Tạo ads trong 60 giây",
        cta: "Nhận demo miễn phí",
        primary: "#0A0F2C",
        accent: "#2563EB",
        highlight: "#FACC15"
      }}
    />
  );
}
