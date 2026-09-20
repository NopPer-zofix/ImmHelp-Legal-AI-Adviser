import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Check, Copy, RotateCcw } from 'lucide-react';
import { describeTopics } from '../lib/topics';
import Sponsored from './Sponsored';

const markdownComponents = {
  a: ({ node, ...props }) => <a {...props} target="_blank" rel="noreferrer" />,
  table: ({ node, ...props }) => (
    <div className="table-wrap">
      <table {...props} />
    </div>
  ),
};

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      className="icon-btn icon-btn--small"
      aria-label={copied ? 'Copied' : 'Copy answer'}
      title={copied ? 'Copied' : 'Copy'}
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setCopied(true);
          setTimeout(() => setCopied(false), 1500);
        } catch {
          /* clipboard blocked — nothing useful to show */
        }
      }}
    >
      {copied ? <Check size={15} /> : <Copy size={15} />}
    </button>
  );
}

export default function Message({ message, onRetry, canRetry }) {
  if (message.role === 'user') {
    return (
      <div className="msg msg--user">
        <div className="bubble">{message.content}</div>
      </div>
    );
  }

  if (message.error) {
    return (
      <div className="msg msg--error" role="alert">
        <p>{message.content}</p>
        {canRetry && (
          <button className="btn btn-ghost btn-small" onClick={onRetry}>
            <RotateCcw size={14} /> Try again
          </button>
        )}
      </div>
    );
  }

  const source = describeTopics(message.topics);

  return (
    <div className="msg msg--assistant">
      <div className="prose">
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
          {message.content}
        </ReactMarkdown>
      </div>
      <div className="msg-actions">
        <CopyButton text={message.content} />
        {message.model && <span className="msg-model">{message.model}</span>}
        {source && <span className="msg-source">{source}</span>}
      </div>
      <Sponsored ad={message.advertisement} />
    </div>
  );
}
