import { router } from 'kea-router'
import { expectLogic } from 'kea-test-utils'

import { FEATURE_FLAGS } from 'lib/constants'
import { featureFlagLogic } from 'lib/logic/featureFlagLogic'
import { removeProjectIdIfPresent } from 'lib/utils/kea-router'
import { urls } from 'scenes/urls'

import { useMocks } from '~/mocks/jest'
import { initKeaTests } from '~/test/init'

import { canvasSceneLogic } from './canvasSceneLogic'

jest.mock('./deleteCanvasWithUndo', () => ({ deleteCanvasWithUndo: jest.fn() }))

const CANVAS_ID = 'canvas-1'
const DATA_DRIFT = {
    status: 'drift',
    checked_at: '2026-10-05T03:41:00Z',
    missing: { events: ['signup completed'], properties: [], tables: ['stripe_charges'] },
}

describe('canvasSceneLogic', () => {
    let releaseTaskRequest: () => void = () => {}
    let fixRequestBodies: Record<string, unknown>[] = []

    beforeEach(() => {
        fixRequestBodies = []
        const taskRequestReleased = new Promise<void>((resolve) => {
            releaseTaskRequest = resolve
        })
        useMocks({
            get: {
                '/api/projects/:team_id/canvases/:id/view/': {
                    canvas: {
                        id: CANVAS_ID,
                        name: 'Untitled canvas',
                        kind: 'freeform',
                        channel: 'space-1',
                        template_id: 'freeform',
                        generation_task_id: null,
                        published_build_id: null,
                    },
                    published_build: null,
                    current_version_id: null,
                    has_active_build: false,
                    source: null,
                    layout: null,
                    sandbox_document_url: null,
                },
                '/api/projects/:team_id/canvases/:id/builds/': { builds: [], published_build_id: null },
                '/api/projects/:team_id/canvases/:id/data_check/': DATA_DRIFT,
                '/api/projects/:team_id/task_channels/:id/': { id: 'space-1', name: 'me', system_role: 'personal' },
            },
            post: {
                '/api/projects/:team_id/canvases/:id/request_fix/': async ({ request }) => {
                    fixRequestBodies.push((await request.json()) as Record<string, unknown>)
                    return [200, { task_id: 'task-9', dispatch_outcome: 'dispatched' }]
                },
                '/api/projects/:team_id/tasks/:id/run/': [
                    201,
                    { id: 'task-1', title: 'Daily signups', latest_run: { status: 'queued' } },
                ],
                '/api/projects/:team_id/tasks/': async () => {
                    await taskRequestReleased
                    return [403, { error: 'Agent-started task runs are not available for this project' }]
                },
            },
        })
        initKeaTests()
    })

    it('keeps the composer on screen while a run starts and after it fails to start', async () => {
        const logic = canvasSceneLogic({ id: CANVAS_ID })
        logic.mount()
        await expectLogic(logic).toDispatchActions(['loadViewSuccess'])
        expect(logic.values.bodyState).toEqual('empty')

        logic.actions.generateCanvas('A chart of daily signups', false)
        expect(logic.values.generationStarting).toBe(true)
        expect(logic.values.bodyState).toEqual('empty')

        releaseTaskRequest()
        await expectLogic(logic).toDispatchActions(['generationFinished'])
        expect(logic.values.bodyState).toEqual('empty')
        // The side panel and the composer say why, rather than only a toast that disappears.
        expect(logic.values.generationError).toEqual('Agent-started task runs are not available for this project')
    })

    it('stops generating when the agent turn ends while the cloud run stays open', async () => {
        const logic = canvasSceneLogic({ id: CANVAS_ID })
        logic.mount()
        await expectLogic(logic).toDispatchActions(['loadViewSuccess'])
        logic.actions.canvasUpdated({ ...logic.values.canvas!, generation_task_id: 'task-1' })
        logic.actions.loadGenerationTaskSuccess({
            id: 'task-1',
            title: 'Daily signups',
            latest_run: { id: 'run-1', status: 'in_progress' },
        })
        expect(logic.values.isGenerating).toBe(true)

        logic.actions.setAgentTurn('run-1', false)
        expect(logic.values.isGenerating).toBe(false)
        expect(logic.values.generationPhase).toBeNull()

        logic.actions.setAgentTurn('run-1', true)
        expect(logic.values.isGenerating).toBe(true)
    })

    it('shows the nightly data drift result and sends its fix request as a data drift', async () => {
        const logic = canvasSceneLogic({ id: CANVAS_ID })
        logic.mount()
        await expectLogic(logic).toDispatchActions(['loadViewSuccess', 'loadDataCheckSuccess'])
        expect(logic.values.dataDrift).toEqual(DATA_DRIFT)

        logic.actions.requestFix({ buildId: 'build-1', errorType: 'data_drift' })
        await expectLogic(logic).toDispatchActions(['requestFixFinished'])
        expect(fixRequestBodies).toEqual([{ build_id: 'build-1', error_type: 'data_drift' }])
        expect(logic.values.fixTaskId).toEqual('task-9')
    })

    describe('space links', () => {
        beforeEach(() => {
            featureFlagLogic.mount()
        })

        it('links the space breadcrumb and returns to the space after delete in the rail navigation', async () => {
            featureFlagLogic.actions.setFeatureFlags([], { [FEATURE_FLAGS.TODAY_RAIL_NAV]: true })
            const logic = canvasSceneLogic({ id: CANVAS_ID })
            logic.mount()
            await expectLogic(logic).toDispatchActions(['loadViewSuccess', 'loadSpaceSuccess'])

            expect(logic.values.breadcrumbs[0]).toMatchObject({ key: 'canvas-space', path: urls.taskSpace('space-1') })

            logic.actions.deleteCanvas()
            expect(removeProjectIdIfPresent(router.values.location.pathname)).toEqual(urls.taskSpace('space-1'))
        })

        it('keeps the space name without a link and returns to the views list in the standard navigation', async () => {
            featureFlagLogic.actions.setFeatureFlags([], { [FEATURE_FLAGS.SMALL_SOFTWARE_APPS]: true })
            const logic = canvasSceneLogic({ id: CANVAS_ID })
            logic.mount()
            await expectLogic(logic).toDispatchActions(['loadViewSuccess', 'loadSpaceSuccess'])

            expect(logic.values.breadcrumbs[0]).toMatchObject({ key: 'canvas-space' })
            expect(logic.values.breadcrumbs[0].path).toBeUndefined()

            logic.actions.deleteCanvas()
            expect(removeProjectIdIfPresent(router.values.location.pathname)).toEqual(urls.views())
        })
    })
})
