import './SendPreview.css';

export function SendPreview({ payload, onConfirm, onCancel }: {
  payload: unknown;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="send-preview-backdrop">
      <section className="send-preview" role="dialog" aria-modal="true" aria-labelledby="send-preview-title">
        <h2 id="send-preview-title">OpenAIへの送信内容を確認</h2>
        <p>以下のデータをOpenAIに送信して分析します。機密情報が含まれていないか確認してください。</p>
        <pre tabIndex={0}>{JSON.stringify(payload, null, 2)}</pre>
        <div className="send-preview-actions">
          <button className="button-secondary" type="button" onClick={onCancel}>キャンセル</button>
          <button className="button-primary" type="button" onClick={onConfirm}>確認して送信</button>
        </div>
      </section>
    </div>
  );
}
