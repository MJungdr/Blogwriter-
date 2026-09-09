import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ImageIcon } from "lucide-react";

interface BlogInputFormProps {
  onSubmit: (
    topic: string,
    articleType: ArticleType,
    options: OptionalContentOptions,
  ) => void;
  loading: boolean;
}

export type ArticleType =
  | "auto"
  | "research"
  | "ai_tool"
  | "global_life"
  | "hybrid";

export type OptionalContentState = "auto" | "include" | "exclude";

export interface OptionalContentOptions {
  mimiExample: OptionalContentState;
  workflow: OptionalContentState;
  myView: OptionalContentState;
}

const BlogInputForm: React.FC<BlogInputFormProps> = ({ onSubmit, loading }) => {
  const [topic, setTopic] = useState("");
  const [articleType, setArticleType] = useState<ArticleType>("auto");
  const [mimiExample, setMimiExample] = useState<OptionalContentState>("auto");
  const [workflow, setWorkflow] = useState<OptionalContentState>("auto");
  const [myView, setMyView] = useState<OptionalContentState>("auto");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (topic.trim()) {
      onSubmit(topic.trim(), articleType, { mimiExample, workflow, myView });
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
          A topic-matched Unsplash image will be selected for your article
        </p>
      </div>
      <fieldset className="space-y-3 rounded-md border p-4">
        <legend className="px-1 text-sm font-medium">Optional sections</legend>
        <p className="text-sm text-neutral-500 dark:text-neutral-400">
          Control these independently for this article.
        </p>
        <div className="space-y-2">
          <Label htmlFor="mimi-example">Mimi&apos;s Example</Label>
          <select
            id="mimi-example"
            value={mimiExample}
            onChange={(e) => setMimiExample(e.target.value as OptionalContentState)}
            disabled={loading}
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          >
            <option value="auto">Auto</option>
            <option value="include">Include</option>
            <option value="exclude">Exclude</option>
          </select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="workflow">Workflow</Label>
          <select
            id="workflow"
            value={workflow}
            onChange={(e) => setWorkflow(e.target.value as OptionalContentState)}
            disabled={loading}
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          >
            <option value="auto">Auto</option>
            <option value="include">Include</option>
            <option value="exclude">Exclude</option>
          </select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="my-view">My View</Label>
          <select
            id="my-view"
            value={myView}
            onChange={(e) => setMyView(e.target.value as OptionalContentState)}
            disabled={loading}
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          >
            <option value="auto">Auto</option>
            <option value="include">Include</option>
            <option value="exclude">Exclude</option>
          </select>
        </div>
      </fieldset>
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
          <option value="research">Biomedical Science &amp; Therapeutics</option>
          <option value="ai_tool">AI Tool</option>
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
