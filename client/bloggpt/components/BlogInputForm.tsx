import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ImageIcon } from "lucide-react";

interface BlogInputFormProps {
  onSubmit: (topic: string, articleType: ArticleType) => void;
  loading: boolean;
}

export type ArticleType =
  | "auto"
  | "biomedical_science"
  | "ai_research_tools"
  | "global_life";

const BlogInputForm: React.FC<BlogInputFormProps> = ({ onSubmit, loading }) => {
  const [topic, setTopic] = useState("");
  const [articleType, setArticleType] = useState<ArticleType>("auto");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (topic.trim()) {
      onSubmit(topic.trim(), articleType);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="topic">Blog Topic</Label>
        <Input
          id="topic"
          type="text"
          placeholder="Enter your blog topic"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          required
        />
        <p className="text-sm text-neutral-500 flex items-center dark:text-neutral-400">
          <ImageIcon className="w-4 h-4 mr-2" />
          An image will be generated based on your topic
        </p>
      </div>
      <div className="space-y-2">
        <Label htmlFor="article-type">Article Type</Label>
        <select
          id="article-type"
          value={articleType}
          onChange={(e) => setArticleType(e.target.value as ArticleType)}
          disabled={loading}
          className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <option value="auto">Auto-detect (recommended)</option>
          <option value="biomedical_science">Biomedical Science &amp; Therapeutics</option>
          <option value="ai_research_tools">AI Tools &amp; Research Workflows</option>
          <option value="global_life">Global Life</option>
        </select>
        <p className="text-sm text-neutral-500 dark:text-neutral-400">
          Choose a writing mode or let BlogGPT select the dominant topic.
        </p>
      </div>
      <Button
        type="submit"
        disabled={loading || !topic.trim()}
        className="w-full"
      >
        Generate Blog with Image
      </Button>
    </form>
  );
};

export default BlogInputForm;
