import { useMutation } from '@tanstack/react-query'
import { type DragEvent, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'

import { api, ApiError } from '../../api/client'
import type { AcceptedCase } from '../../api/types'
import { caseContract } from './caseContract'
import { fieldPath, formatPath, locate, parseCase } from './jsonText'

type LocalProblem = { kind: 'empty' } | { kind: 'syntax'; line: number; column: number }

// 1152 container minus 2 x 24 padding = 1104 = 720 editor + 24 gap + 360 result panel.
export function NewCasePage() {
  const { t } = useTranslation()
  const [text, setText] = useState('')
  const [fileName, setFileName] = useState<string>()
  const [problem, setProblem] = useState<LocalProblem>()
  const editor = useRef<HTMLTextAreaElement>(null)
  const resultHeading = useRef<HTMLHeadingElement>(null)
  const submit = useMutation<AcceptedCase, Error, unknown>({ mutationFn: (body) => api.submitCase(body) })

  useEffect(() => {
    if (submit.isSuccess || submit.isError) resultHeading.current?.focus()
  }, [submit.isSuccess, submit.isError])

  function onSubmit() {
    if (!text.trim()) return setProblem({ kind: 'empty' })
    const parsed = parseCase(text)
    if (!parsed.ok) {
      setProblem({ kind: 'syntax', line: parsed.line, column: parsed.column })
      return
    }
    setProblem(undefined)
    submit.mutate(parsed.value)
  }

  async function load(file: File) {
    setText(await file.text())
    setFileName(file.name)
    setProblem(undefined)
    submit.reset()
  }

  function onDrop(event: DragEvent) {
    const file = event.dataTransfer.files[0]
    if (!file) return
    event.preventDefault()
    void load(file)
  }

  function showInEditor(path: (string | number)[]) {
    const area = editor.current
    const range = locate(text, path)
    if (!area || !range) return
    area.focus()
    area.setSelectionRange(range.start, range.end)
    const lineHeight = parseFloat(getComputedStyle(area).lineHeight) || 20
    area.scrollTop = Math.max(0, (range.line - 3) * lineHeight)
  }

  const summary = summarize(text)

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl">{t('newCase.title')}</h1>
        <p className="mt-1 text-[15px] text-muted">{t('newCase.subtitle')}</p>
      </div>

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
        <section className="rounded-2xl bg-surface p-5">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
            <label htmlFor="case-json" className="text-base font-medium">
              {t('newCase.editorLabel')}
            </label>
            <label className="inline-flex h-9 cursor-pointer items-center rounded-full border border-control px-4 text-sm font-medium hover:border-aligo-blanco focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-aligo-rojo">
              {t('newCase.upload')}
              <input
                type="file"
                accept="application/json,.json"
                className="sr-only"
                onChange={(event) => {
                  const file = event.target.files?.[0]
                  if (file) void load(file)
                  event.target.value = ''
                }}
              />
            </label>
          </div>
          <textarea
            id="case-json"
            ref={editor}
            value={text}
            onChange={(event) => {
              setText(event.target.value)
              setFileName(undefined)
              setProblem(undefined)
            }}
            onDragOver={(event) => event.preventDefault()}
            onDrop={onDrop}
            spellCheck={false}
            wrap="off"
            aria-describedby="case-json-help"
            aria-invalid={problem ? true : undefined}
            placeholder={t('newCase.placeholder')}
            className="block h-[28rem] w-full resize-y rounded-xl bg-ground p-4 font-mono text-[13px] leading-5 text-aligo-blanco placeholder:text-faint focus:outline-2 focus:outline-aligo-rojo"
          />
          <div className="mt-4 flex flex-wrap items-center justify-between gap-4">
            <p id="case-json-help" className="text-sm text-muted" aria-live="polite">
              {problem?.kind === 'empty' && <span className="border-l-4 border-state-error pl-2 text-aligo-blanco">{t('newCase.empty')}</span>}
              {problem?.kind === 'syntax' && (
                <span className="border-l-4 border-state-error pl-2 text-aligo-blanco">{t('newCase.syntax', { line: problem.line, column: problem.column })}</span>
              )}
              {!problem && (fileName ? t('newCase.loadedFile', { name: fileName }) : summary && t('newCase.summary', summary))}
            </p>
            <button
              type="button"
              onClick={onSubmit}
              disabled={submit.isPending}
              // White on the brand red is 4.3:1, so the resting fill is the darker brand red, which passes AA.
              className="inline-flex h-9 items-center rounded-full bg-aligo-rojo-oscuro px-5 text-sm font-bold text-aligo-blanco hover:bg-aligo-rojo-medio disabled:cursor-wait disabled:opacity-80"
            >
              {submit.isPending ? t('newCase.submitting') : t('newCase.submit')}
            </button>
          </div>
        </section>

        <section aria-live="polite" className="rounded-2xl bg-surface p-5">
          <Result
            headingRef={resultHeading}
            state={submit}
            onRetry={onSubmit}
            onShow={showInEditor}
          />
        </section>
      </div>
    </div>
  )
}

function summarize(text: string) {
  const parsed = text.trim() ? parseCase(text) : undefined
  if (!parsed?.ok || typeof parsed.value !== 'object' || parsed.value === null) return undefined
  const value = parsed.value as { case_id?: unknown; alerts?: unknown }
  if (typeof value.case_id !== 'string' || !Array.isArray(value.alerts)) return undefined
  return { caseId: value.case_id, count: value.alerts.length }
}

interface ResultProps {
  headingRef: React.RefObject<HTMLHeadingElement | null>
  state: { isIdle: boolean; isPending: boolean; data?: AcceptedCase; error: Error | null }
  onRetry: () => void
  onShow: (path: (string | number)[]) => void
}

function Result({ headingRef, state, onRetry, onShow }: ResultProps) {
  const { t } = useTranslation()
  const heading = (text: string) => (
    <h2 ref={headingRef} tabIndex={-1} className="text-base">
      {text}
    </h2>
  )

  if (state.data) {
    return (
      <div className="border-l-4 border-state-ok pl-4">
        {heading(t('newCase.accepted.title'))}
        <p className="mt-1 text-sm text-muted">{t('newCase.accepted.body', { id: state.data.submitted_case_id })}</p>
        <p className="mt-4 text-xs text-muted">{t('newCase.accepted.uuid')}</p>
        <CopyValue value={state.data.case_id} />
      </div>
    )
  }

  if (state.error) {
    const error = state.error instanceof ApiError ? state.error : new ApiError(0, 'network')
    if (error.status === 422 && error.issues.length) {
      return (
        <div className="border-l-4 border-state-error pl-4">
          {heading(t('newCase.invalid.title', { count: error.issues.length }))}
          <p className="mt-1 text-sm text-muted">{t('newCase.invalid.body')}</p>
          <ul className="mt-4 divide-y divide-control">
            {error.issues.map((issue, index) => {
              const path = fieldPath(issue.loc)
              return (
                <li key={index} className="py-3">
                  <div className="flex flex-wrap items-baseline gap-x-2">
                    <span className="flex-none rounded bg-ground px-1.5 text-xs font-medium">{issue.rule}</span>
                    <code className="font-mono text-[13px] break-all">{formatPath(path) || t('newCase.invalid.wholeCase')}</code>
                  </div>
                  <p className="mt-1 text-sm">{issue.msg}</p>
                  <button
                    type="button"
                    onClick={() => onShow(path)}
                    className="mt-1 text-sm font-medium underline decoration-aligo-rojo decoration-2 underline-offset-4 hover:decoration-aligo-blanco"
                  >
                    {t('newCase.invalid.show')}
                  </button>
                </li>
              )
            })}
          </ul>
        </div>
      )
    }
    if (error.status === 409) {
      return (
        <div className="border-l-4 border-state-warn pl-4">
          {heading(t('newCase.duplicate.title'))}
          <p className="mt-1 text-sm text-muted">{t('newCase.duplicate.body')}</p>
        </div>
      )
    }
    return (
      <div className="border-l-4 border-state-error pl-4">
        {heading(error.status === 0 ? t('newCase.offline.title') : t('newCase.failed.title', { status: error.status }))}
        <p className="mt-1 text-sm text-muted">{error.status === 0 ? t('newCase.offline.body') : String(error.detail)}</p>
        <button type="button" onClick={onRetry} className="mt-3 text-sm font-medium underline decoration-aligo-rojo decoration-2 underline-offset-4 hover:decoration-aligo-blanco">
          {t('newCase.retry')}
        </button>
      </div>
    )
  }

  return <Contract pending={state.isPending} />
}

function Contract({ pending }: { pending: boolean }) {
  const { t, i18n } = useTranslation()
  const sources = new Intl.ListFormat(i18n.resolvedLanguage, { type: 'disjunction' }).format(caseContract.sources)
  const list = (items: readonly string[]) => (
    <ul className="mt-2 flex flex-wrap gap-1.5">
      {items.map((item) => (
        <li key={item}>
          <code className="rounded bg-ground px-1.5 py-0.5 font-mono text-[13px]">{item}</code>
        </li>
      ))}
    </ul>
  )

  return (
    <div>
      <h2 className="text-base">{pending ? t('newCase.contract.checking') : t('newCase.contract.title')}</h2>
      <p className="mt-1 text-sm text-muted">
        {t('newCase.contract.alerts', {
          min: caseContract.minAlerts,
          max: caseContract.maxAlerts,
          sources,
        })}
      </p>
      <h3 className="mt-5 text-sm font-medium">{t('newCase.contract.caseFields')}</h3>
      {list(caseContract.caseFields)}
      <h3 className="mt-4 text-sm font-medium">{t('newCase.contract.alertFields')}</h3>
      {list(caseContract.alertFields)}
    </div>
  )
}

function CopyValue({ value }: { value: string }) {
  const { t } = useTranslation()
  const [copied, setCopied] = useState(false)

  return (
    <div className="mt-1 flex items-center gap-3">
      <code className="min-w-0 font-mono text-[13px] break-all">{value}</code>
      {navigator.clipboard && (
        <button
          type="button"
          onClick={() => void navigator.clipboard.writeText(value).then(() => setCopied(true))}
          className="flex-none text-sm font-medium underline decoration-aligo-rojo decoration-2 underline-offset-4 hover:decoration-aligo-blanco"
        >
          {copied ? t('newCase.accepted.copied') : t('newCase.accepted.copy')}
        </button>
      )}
    </div>
  )
}
