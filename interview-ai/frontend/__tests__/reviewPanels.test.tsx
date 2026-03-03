import { render, screen } from "@testing-library/react";

import { AnswerComparison } from "@/components/review/AnswerComparison";
import { AntiTemplateWarning } from "@/components/review/AntiTemplateWarning";
import { ImprovementList } from "@/components/review/ImprovementList";
import { StructuralCheck } from "@/components/review/StructuralCheck";

describe("review panel components", () => {
  it("does not render anti-template banner when warning is null", () => {
    const { container } = render(<AntiTemplateWarning warning={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders anti-template banner when warning exists", () => {
    render(<AntiTemplateWarning warning="检测到模板化表达过多" />);
    expect(screen.getByText("反模板化提醒")).toBeInTheDocument();
    expect(screen.getByText("检测到模板化表达过多")).toBeInTheDocument();
  });

  it("renders structural check labels", () => {
    render(
      <StructuralCheck
        check={{
          is_complete: false,
          present_elements: ["表明态度", "分析原因"],
          missing_elements: ["长效机制"],
        }}
      />,
    );

    expect(screen.getByText("已覆盖要素")).toBeInTheDocument();
    expect(screen.getByText("缺失要素")).toBeInTheDocument();
    expect(screen.getByText("长效机制")).toBeInTheDocument();
  });

  it("renders fallback when suggestions are empty", () => {
    render(<ImprovementList suggestions={[]} />);
    expect(screen.getByText("暂无改进建议。")).toBeInTheDocument();
  });

  it("renders dual-column answer comparison content", () => {
    render(<AnswerComparison userAnswer="我的回答" modelAnswer="示范回答" />);
    expect(screen.getByText("考生原文")).toBeInTheDocument();
    expect(screen.getByText("AI 示范答案")).toBeInTheDocument();
    expect(screen.getByText("我的回答")).toBeInTheDocument();
    expect(screen.getByText("示范回答")).toBeInTheDocument();
  });
});
