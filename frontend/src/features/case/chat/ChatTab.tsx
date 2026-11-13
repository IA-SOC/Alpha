import { useMutation, useMutationState, useQuery, useQueryClient } from '@tanstack/react-query'
import { type FormEvent, type KeyboardEvent, useEffect, useId, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, ApiError } from '../../../api/client'
import type { ChatEvidenceItem, ChatMessage, Investigation } from '../../../api/types'
import { useSession } from '../../../session/session'
import { PrimaryButton, TextButton } from '../../../ui/buttons'
import { AlertId, Empty } from '../report/parts'
import { formatUtc } from '../report/format'
import { describeRef, type RefGroup, refGroups, type RefInfo } from './evidence'
import { chatKey, maxMessageLength } from './keys'

// A conversation with Gemini about this case only. The backend keeps the history, sends Gemini
// the case, the report and the last 20 messages, and checks every evidence key in the answer.
export function ChatTab({ investigation }: { investigation: Investigation }) {
  const { t } = useTranslation()
  const caseId = investigation.case_id
  const [inspected, setInspected] = useState<string>()
  const [attached, setAttached] = useState<string[]>([])
  const history = useQuery({ queryKey: chatKey(caseId), queryFn: () => api.getMessages(caseId) })
  // Keyed by the run, since a rerun retires every investigation key.
  const evidence = useQuery({
    queryKey: ['chatEvidence', caseId, investigation.run_id],
    queryFn: () => api.getChatEvidence(caseId),
  })
  const catalog = evidence.data?.evidence
  const describe = (key: string) => describeRef(key, catalog, investigation.run_id, t)
  const toggle = (key: string) =>
    setAttached((current) => (current.includes(key) ? current.filter((entry) => entry !== key) : [...current, key]))

  return (
    <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
      <section aria-labelledby="chat-title" className="rounded-2xl bg-surface p-5">
        <h2 id="chat-title" className="text-base">
          {t('chat.title')}
        </h2>
        <p className="mt-1 text-sm text-muted">{t('chat.intro')}</p>
        <Thread
          caseId={caseId}
          messages={history.data?.messages}
          loading={history.isPending}
          failed={history.isError}
          onRetry={() => void history.refetch()}
          describe={describe}
          onInspect={setInspected}
        />
        <Composer
          caseId={caseId}
          attached={attached.map(describe)}
          onDetach={toggle}
          onSent={() => setAttached([])}
          suggest={(history.data?.messages.length ?? 0) === 0}
        />
      </section>
      <EvidenceRail
        catalog={catalog}
        loading={evidence.isPending}
        failed={evidence.isError}
        describe={describe}
        inspected={inspected ? describe(inspected) : undefined}
        onInspect={setInspected}
        attached={attached}
        onToggle={toggle}
      />
    </div>
  )
}

interface ThreadProps {
  caseId: string
  messages?: ChatMessage[]
  loading: boolean
  failed: boolean
  onRetry: () => void
  describe: (key: string) => RefInfo
  onInspect: (key: string) => void
}

function Thread({ caseId, messages, loading, failed, onRetry, describe, onInspect }: ThreadProps) {
  const { t } = useTranslation()
  const last = useRef<HTMLLIElement>(null)
  const count = messages?.length ?? 0
  const seen = useRef(count)
  // A new answer comes into view, but opening the tab on a long history does not jump.
  useEffect(() => {
    if (count > seen.current) last.current?.scrollIntoView?.({ block: 'nearest' })
    seen.current = count
  }, [count])
  const sending = useSendState(caseId)

  if (loading) return <Empty>{t('chat.loading')}</Empty>
  if (failed)
    return (
      <div role="alert" className="mt-4 border-l-4 border-state-error pl-4">
        <p className="text-sm">{t('chat.historyFailed')}</p>
        <TextButton onClick={onRetry} className="mt-2">
          {t('newCase.retry')}
        </TextButton>
      </div>
    )

  return (
    <ol aria-label={t('chat.thread')} className="mt-5 space-y-4">
      {count === 0 && !sending && (
        <li className="rounded-xl border border-dashed border-control px-4 py-3 text-sm text-muted">{t('chat.empty')}</li>
      )}
      {messages?.map((message, index) => (
        <li key={`${message.created_at}-${index}`} ref={index === count - 1 ? last : undefined}>
          <Message message={message} describe={describe} onInspect={onInspect} />
        </li>
      ))}
      {sending && (
        <li>
          <Message
            message={{ role: 'user', content: sending.message, evidence_refs: sending.refs, created_at: '' }}
            describe={describe}
            onInspect={onInspect}
          />
          <p role="status" className="mt-3 text-sm text-muted">
            {t('chat.answering')}
          </p>
        </li>
      )}
    </ol>
  )
}

function Message({
  message,
  describe,
  onInspect,
}: {
  message: ChatMessage
  describe: (key: string) => RefInfo
  onInspect: (key: string) => void
}) {
  const { t } = useTranslation()
  const mine = message.role === 'user'

  return (
    <article className={`rounded-xl p-4 ${mine ? 'bg-ground' : 'border border-control'}`}>
      <header className="flex flex-wrap items-baseline justify-between gap-x-4 text-xs text-muted">
        <span className="font-medium text-aligo-blanco">
          {mine ? (message.analyst_id ?? t('chat.you')) : t('chat.gemini')}
        </span>
        {message.created_at && <time dateTime={message.created_at}>{formatUtc(message.created_at)}</time>}
      </header>
      {/* The model's text and the analyst's, as written. Never rendered as HTML. */}
      <p className="mt-2 text-sm whitespace-pre-wrap">{message.content}</p>
      {message.evidence_refs.length > 0 && (
        <div className="mt-3">
          <p className="text-xs text-muted">{t(mine ? 'chat.askedAbout' : 'chat.cites', { count: message.evidence_refs.length })}</p>
          <ul className="mt-1 flex flex-wrap gap-2">
            {message.evidence_refs.map((key) => {
              const info = describe(key)
              return (
                <li key={key}>
                  <RefButton info={info} onClick={() => onInspect(key)} />
                </li>
              )
            })}
          </ul>
        </div>
      )}
    </article>
  )
}

function RefButton({ info, onClick }: { info: RefInfo; onClick: () => void }) {
  const { t } = useTranslation()
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={t('chat.inspect', { label: info.label })}
      className={`max-w-full truncate rounded border px-2 py-0.5 text-left text-xs hover:border-aligo-blanco ${
        info.stale ? 'border-dashed border-control text-muted' : 'border-control'
      }`}
    >
      {info.label}
    </button>
  )
}

// The question being sent, shared between the composer and the thread through the mutation cache.
const sendKey = (caseId: string) => ['chat-send', caseId] as const

interface SendVariables {
  message: string
  refs: string[]
}

function useSendState(caseId: string): SendVariables | undefined {
  return useMutationState({
    filters: { mutationKey: sendKey(caseId), status: 'pending' },
    select: (mutation) => mutation.state.variables as SendVariables,
  }).at(-1)
}

interface ComposerProps {
  caseId: string
  attached: RefInfo[]
  onDetach: (key: string) => void
  onSent: () => void
  suggest: boolean
}

function Composer({ caseId, attached, onDetach, onSent, suggest }: ComposerProps) {
  const { t } = useTranslation()
  const id = useId()
  const session = useSession()
  const queryClient = useQueryClient()
  const [draft, setDraft] = useState('')
  const [blank, setBlank] = useState(false)
  const send = useMutation<unknown, Error, SendVariables>({
    mutationKey: sendKey(caseId),
    mutationFn: ({ message, refs }) => api.sendMessage(caseId, session?.analyst ?? '', message, refs),
    // The backend stores the question and the answer together, so the history is read again.
    onSuccess: () => queryClient.invalidateQueries({ queryKey: chatKey(caseId) }),
  })

  function submit(event?: FormEvent) {
    event?.preventDefault()
    if (send.isPending) return
    if (!draft.trim()) {
      setBlank(true)
      return
    }
    setBlank(false)
    send.mutate(
      { message: draft, refs: attached.map((info) => info.key) },
      {
        onSuccess: () => {
          setDraft('')
          onSent()
        },
      },
    )
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) submit()
  }

  const suggestions = [t('chat.suggest.support'), t('chat.suggest.change'), t('chat.suggest.next')]

  return (
    <form onSubmit={submit} className="mt-6 border-t border-rule pt-5" noValidate>
      {suggest && !send.isPending && (
        <div className="mb-4">
          <p className="text-xs text-muted">{t('chat.suggest.title')}</p>
          <ul className="mt-2 flex flex-wrap gap-2">
            {suggestions.map((text) => (
              <li key={text}>
                <button
                  type="button"
                  onClick={() => setDraft(text)}
                  className="rounded-full border border-control px-3 py-1 text-xs hover:border-aligo-blanco"
                >
                  {text}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
      <label htmlFor={id} className="text-sm font-medium">
        {t('chat.question')}
      </label>
      <textarea
        id={id}
        value={draft}
        rows={3}
        maxLength={maxMessageLength}
        aria-invalid={blank ? true : undefined}
        aria-describedby={`${id}-hint`}
        onChange={(event) => {
          setDraft(event.target.value)
          if (blank) setBlank(false)
        }}
        onKeyDown={onKeyDown}
        className="mt-2 block w-full resize-y rounded-xl bg-ground p-4 text-sm text-aligo-blanco focus:outline-2 focus:outline-aligo-rojo"
      />
      <p id={`${id}-hint`} className="mt-1 text-xs text-muted">
        {t('chat.hint', { count: draft.length, max: maxMessageLength })}
      </p>
      {blank && (
        <p className="mt-1 border-l-4 border-state-error pl-2 text-sm" role="alert">
          {t('chat.blank')}
        </p>
      )}

      {attached.length > 0 && (
        <div className="mt-3">
          <p className="text-xs text-muted">{t('chat.attached', { count: attached.length })}</p>
          <ul className="mt-1 flex flex-wrap gap-2">
            {attached.map((info) => (
              <li key={info.key} className="flex max-w-full items-center gap-1 rounded border border-control px-2 py-0.5 text-xs">
                <span className="truncate">{info.label}</span>
                <button type="button" onClick={() => onDetach(info.key)} aria-label={t('chat.detach', { label: info.label })} className="px-1 text-muted hover:text-aligo-blanco">
                  ×
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {send.isError && <SendFailed error={send.error} />}

      <PrimaryButton type="submit" disabled={send.isPending} className="mt-4">
        {send.isPending ? t('chat.sending') : t('chat.send')}
      </PrimaryButton>
    </form>
  )
}

// What each backend answer means for the analyst, from app/api/routes/chat.py. The draft stays.
function SendFailed({ error }: { error: Error }) {
  const { t } = useTranslation()
  const status = error instanceof ApiError ? error.status : -1
  const detail = error instanceof ApiError && typeof error.detail === 'string' ? error.detail : ''
  const known: Record<number, string> = {
    0: 'offline',
    403: 'analyst',
    409: 'notReady',
    422: 'invalid',
    502: 'rejected',
    503: 'notConfigured',
    504: 'timeout',
  }
  const reason = known[status] ?? 'other'

  return (
    <div role="alert" className="mt-4 border-l-4 border-state-error pl-4">
      <p className="text-sm font-medium">{t(`chat.failed.${reason}`, { status })}</p>
      {detail && reason !== 'offline' && <p className="mt-1 text-sm text-muted">{detail}</p>}
      <p className="mt-1 text-sm text-muted">{t('chat.failed.kept')}</p>
    </div>
  )
}

interface EvidenceRailProps {
  catalog?: Record<string, ChatEvidenceItem>
  loading: boolean
  failed: boolean
  describe: (key: string) => RefInfo
  inspected?: RefInfo
  onInspect: (key: string) => void
  attached: string[]
  onToggle: (key: string) => void
}

function EvidenceRail({ catalog, loading, failed, describe, inspected, onInspect, attached, onToggle }: EvidenceRailProps) {
  const { t } = useTranslation()
  const groups = new Map<RefGroup, RefInfo[]>()
  for (const key of Object.keys(catalog ?? {})) {
    const info = describe(key)
    if (!info.group) continue
    groups.set(info.group, [...(groups.get(info.group) ?? []), info])
  }

  return (
    <div className="space-y-6">
      {inspected && <Inspector info={inspected} />}
      <section aria-labelledby="chat-evidence-title" className="rounded-2xl bg-surface p-5">
        <h2 id="chat-evidence-title" className="text-base">
          {t('chat.evidence.title')}
        </h2>
        <p className="mt-1 text-sm text-muted">{t('chat.evidence.intro')}</p>
        {loading && <Empty>{t('chat.evidence.loading')}</Empty>}
        {failed && <Empty>{t('chat.evidence.failed')}</Empty>}
        <div className="mt-3 max-h-[32rem] space-y-4 overflow-y-auto pr-1">
          {refGroups
            .filter((group) => groups.has(group))
            .map((group) => (
              <fieldset key={group}>
                <legend className="text-xs text-muted">{t(`chat.evidence.groups.${group}`)}</legend>
                <ul className="mt-1 space-y-1">
                  {groups.get(group)!.map((info) => (
                    <li key={info.key} className="flex items-start gap-2 text-sm">
                      <input
                        type="checkbox"
                        checked={attached.includes(info.key)}
                        onChange={() => onToggle(info.key)}
                        aria-label={t('chat.attach', { label: info.label })}
                        className="mt-1 accent-aligo-rojo"
                      />
                      <button
                        type="button"
                        onClick={() => onInspect(info.key)}
                        aria-label={t('chat.inspect', { label: info.label })}
                        className="min-w-0 text-left hover:underline"
                      >
                        <span className="line-clamp-2 break-words">{info.label}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              </fieldset>
            ))}
        </div>
      </section>
    </div>
  )
}

// One piece of evidence as the backend holds it, so the analyst can check what Gemini cited.
function Inspector({ info }: { info: RefInfo }) {
  const { t } = useTranslation()
  const heading = useRef<HTMLHeadingElement>(null)
  useEffect(() => heading.current?.focus(), [info.key])

  return (
    <section aria-labelledby="inspector-title" className="rounded-2xl bg-surface p-5 outline-2 outline-control">
      <h2 id="inspector-title" ref={heading} tabIndex={-1} className="text-base break-words">
        {info.label}
      </h2>
      <p className="mt-1 text-xs text-muted">
        {info.item?.source === 'submitted_case' ? t('chat.evidence.fromCase') : t('chat.evidence.fromRun')}
      </p>
      {info.stale && (
        <p className="mt-3 border-l-4 border-state-warn pl-3 text-sm">{t('chat.evidence.stale')}</p>
      )}
      {info.alertId && (
        <p className="mt-3 text-sm">
          <AlertId id={info.alertId} />
        </p>
      )}
      {info.item && (
        <pre className="mt-3 max-h-80 overflow-auto rounded-xl bg-ground p-3 font-mono text-xs whitespace-pre-wrap break-words">
          {JSON.stringify(info.item.data, null, 2)}
        </pre>
      )}
    </section>
  )
}
