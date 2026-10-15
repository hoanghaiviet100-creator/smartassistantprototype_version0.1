import { ArrowRight, BookOpen, Globe2, Search } from "lucide-react";

interface SuggestedQuestionsProps {
  onChoose: (question: string) => void;
}

const suggestions = [
  {
    title: "Summarize a document",
    description: "Get the key ideas in seconds.",
    question: "Summarize the key points in my documents.",
    icon: BookOpen,
    tone: "lavender",
  },
  {
    title: "Find key details",
    description: "Locate dates, facts, and figures.",
    question: "What are the most important dates and deadlines?",
    icon: Search,
    tone: "mint",
  },
  {
    title: "Compare documents",
    description: "Connect information across files.",
    question: "Compare the main ideas across my documents.",
    icon: Globe2,
    tone: "peach",
  },
];

export function SuggestedQuestions({ onChoose }: SuggestedQuestionsProps) {
  return (
    <section className="suggestion-section" aria-labelledby="suggestions-heading">
      <div className="section-kicker" id="suggestions-heading">GET STARTED</div>
      <div className="suggestion-grid">
        {suggestions.map(({ title, description, question, icon: Icon, tone }) => (
          <button type="button" className="suggestion-card" key={title} onClick={() => onChoose(question)}>
            <span className={`suggestion-icon ${tone}`}><Icon size={17} /></span>
            <strong>{title}</strong>
            <span>{description}</span>
            <ArrowRight size={15} className="suggestion-arrow" />
          </button>
        ))}
      </div>
    </section>
  );
}
