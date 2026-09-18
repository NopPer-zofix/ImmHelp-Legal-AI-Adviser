import { useCallback, useEffect, useState } from 'react';
import { PanelLeftOpen, SquarePen } from 'lucide-react';
import { useChats, titleOf } from '../hooks/useChats';
import { useSubscription } from '../hooks/useSubscription';
import { useMediaQuery } from '../hooks/useMediaQuery';
import { useModel } from '../hooks/useModel';
import Sidebar from './Sidebar';
import Welcome from './Welcome';
import Thread from './Thread';
import Composer from './Composer';
import ComposerGate from './ComposerGate';
import ModelPicker from './ModelPicker';
import UpgradeDialog from './UpgradeDialog';
import Toast from './Toast';

export default function ChatApp({ user, onLogout }) {
  const subscription = useSubscription(user);
  const chats = useChats(user, { onAnswer: subscription.recordMessage });
  const { model, models, select: selectModel } = useModel(user, subscription.isPro);
  const isMobile = useMediaQuery('(max-width: 768px)');
  const [sidebarOpen, setSidebarOpen] = useState(!isMobile);
  const [paywall, setPaywall] = useState(null); // null | 'limit' | 'model' | 'menu' | 'manage'

  useEffect(() => setSidebarOpen(!isMobile), [isMobile]);

  const closeOnMobile = () => isMobile && setSidebarOpen(false);
  const active = chats.activeChat;
  const hasMessages = active && active.messages.length > 0;
  const isPending = chats.pendingId != null;

  // Every way of asking a question goes through here, so the limit can't be skipped in the UI
  const { canSend } = subscription;
  const { send: sendMessage, retry: retryMessage } = chats;

  const send = useCallback(
    async (text) => {
      if (!canSend) {
        setPaywall('limit');
        return false;
      }
      return sendMessage(text, model);
    },
    [canSend, sendMessage, model],
  );

  const retry = () => (canSend ? retryMessage(active.id) : setPaywall('limit'));
  const openUpgrade = () => setPaywall('limit');

  const picker = (
    <ModelPicker
      model={model}
      models={models}
      isPro={subscription.isPro}
      onSelect={selectModel}
      onLocked={() => setPaywall('model')}
    />
  );

  return (
    <div className={`app ${sidebarOpen ? 'is-sidebar-open' : 'is-sidebar-closed'}`}>
      <Sidebar
        user={user}
        chats={chats}
        subscription={subscription}
        onUpgrade={() => setPaywall('menu')}
        onManage={() => setPaywall('manage')}
        onClose={() => setSidebarOpen(false)}
        onNavigate={closeOnMobile}
        onLogout={onLogout}
      />
      {isMobile && sidebarOpen && <div className="scrim" onClick={() => setSidebarOpen(false)} aria-hidden="true" />}

      <main className="main">
        <header className="topbar">
          {!sidebarOpen && (
            <button className="icon-btn" onClick={() => setSidebarOpen(true)} aria-label="Open sidebar">
              <PanelLeftOpen size={18} />
            </button>
          )}
          <h1 className="topbar-title">{hasMessages ? titleOf(active) : ''}</h1>
          {!sidebarOpen && (
            <button className="icon-btn" onClick={chats.startNew} aria-label="New chat">
              <SquarePen size={18} />
            </button>
          )}
        </header>

        {hasMessages ? (
          <>
            <Thread chat={active} pending={chats.pendingId === active.id} onRetry={retry} />
            <div className="dock">
              <ComposerGate subscription={subscription} onUpgrade={openUpgrade}>
                <Composer key={active.id} onSend={send} busy={isPending} picker={picker} />
              </ComposerGate>
              <p className="disclaimer">
                ImmHelp can make mistakes. Confirm important details with professionals.
              </p>
            </div>
          </>
        ) : (
          <Welcome
            key={active?.id ?? 'new'}
            user={user}
            subscription={subscription}
            onSend={send}
            onUpgrade={openUpgrade}
            picker={picker}
            busy={isPending}
            loading={chats.status === 'loading'}
          />
        )}
      </main>

      <UpgradeDialog
        open={paywall != null}
        reason={paywall}
        user={user}
        subscription={subscription}
        onClose={() => setPaywall(null)}
      />
      <Toast message={chats.notice} onDismiss={chats.clearNotice} />
    </div>
  );
}
