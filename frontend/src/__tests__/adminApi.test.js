import { adminApi, assignmentApi, qrApi, enrollmentApi } from '../lib/api';
import api from '../lib/api';

// Mock axios
jest.mock('axios');
import axios from 'axios';

describe('adminApi', () => {
    beforeEach(() => {
        axios.create.mockReturnThis();
    });

    test('listInstitutions calls GET /admin/institutions', async () => {
        axios.get.mockResolvedValue({ data: [] });
        await adminApi.listInstitutions();
        expect(axios.get).toHaveBeenCalledWith('/admin/institutions');
    });

    test('createInstitution calls POST /admin/institutions', async () => {
        const data = { name: 'Test', code: 'TST' };
        axios.post.mockResolvedValue({ data });
        await adminApi.createInstitution(data);
        expect(axios.post).toHaveBeenCalledWith('/admin/institutions', data);
    });

    test('listInstitutionYears calls GET /admin/institutions/{id}/years', async () => {
        axios.get.mockResolvedValue({ data: [] });
        await adminApi.listInstitutionYears('inst-1');
        expect(axios.get).toHaveBeenCalledWith('/admin/institutions/inst-1/years');
    });

    test('listInstitutionBranches calls GET /admin/institutions/{id}/branches', async () => {
        axios.get.mockResolvedValue({ data: [] });
        await adminApi.listInstitutionBranches('inst-1');
        expect(axios.get).toHaveBeenCalledWith('/admin/institutions/inst-1/branches');
    });

    test('createYear calls POST /admin/years', async () => {
        const data = { institution_id: 'inst-1', number: 1, name: 'First Year' };
        axios.post.mockResolvedValue({ data });
        await adminApi.createYear(data);
        expect(axios.post).toHaveBeenCalledWith('/admin/years', data);
    });

    test('listYearSemesters calls GET /admin/years/{id}/semesters', async () => {
        axios.get.mockResolvedValue({ data: [] });
        await adminApi.listYearSemesters('year-1');
        expect(axios.get).toHaveBeenCalledWith('/admin/years/year-1/semesters');
    });

    test('createClass calls POST /admin/classes', async () => {
        const data = { division_id: 'div-1', subject_id: 'sub-1', name: 'Class A' };
        axios.post.mockResolvedValue({ data });
        await adminApi.createClass(data);
        expect(axios.post).toHaveBeenCalledWith('/admin/classes', data);
    });

    test('deleteClass calls DELETE /admin/classes/{id}', async () => {
        axios.delete.mockResolvedValue({ data: { ok: true } });
        await adminApi.deleteClass('class-1');
        expect(axios.delete).toHaveBeenCalledWith('/admin/classes/class-1');
    });
});

describe('assignmentApi', () => {
    beforeEach(() => {
        axios.create.mockReturnThis();
    });

    test('assign calls POST /enrollment/assignments', async () => {
        const data = { class_id: 'c1', teacher_id: 't1' };
        axios.post.mockResolvedValue({ data });
        await assignmentApi.assign(data);
        expect(axios.post).toHaveBeenCalledWith('/enrollment/assignments', data);
    });

    test('listForClass calls GET /enrollment/assignments/class/{id}', async () => {
        axios.get.mockResolvedValue({ data: [] });
        await assignmentApi.listForClass('class-1');
        expect(axios.get).toHaveBeenCalledWith('/enrollment/assignments/class/class-1');
    });

    test('remove calls DELETE /enrollment/assignments/{id}', async () => {
        axios.delete.mockResolvedValue({ data: { ok: true } });
        await assignmentApi.remove('assign-1');
        expect(axios.delete).toHaveBeenCalledWith('/enrollment/assignments/assign-1');
    });
});

describe('qrApi', () => {
    beforeEach(() => {
        axios.create.mockReturnThis();
    });

    test('generate calls POST /qr/classes/{id}/generate', async () => {
        axios.post.mockResolvedValue({ data: {} });
        await qrApi.generate('class-1');
        expect(axios.post).toHaveBeenCalledWith('/qr/classes/class-1/generate');
    });

    test('regenerate calls POST /qr/classes/{id}/regenerate', async () => {
        axios.post.mockResolvedValue({ data: {} });
        await qrApi.regenerate('class-1');
        expect(axios.post).toHaveBeenCalledWith('/qr/classes/class-1/regenerate');
    });

    test('get calls GET /qr/classes/{id}', async () => {
        axios.get.mockResolvedValue({ data: {} });
        await qrApi.get('class-1');
        expect(axios.get).toHaveBeenCalledWith('/qr/classes/class-1');
    });

    test('downloadUrl returns correct URL with format param', () => {
        const url = qrApi.downloadUrl('class-1', 'svg');
        expect(url).toContain('/qr/classes/class-1/download?format=svg');
    });

    test('analytics calls GET /qr/classes/{id}/analytics', async () => {
        axios.get.mockResolvedValue({ data: {} });
        await qrApi.analytics('class-1');
        expect(axios.get).toHaveBeenCalledWith('/qr/classes/class-1/analytics');
    });
});

describe('enrollmentApi', () => {
    beforeEach(() => {
        axios.create.mockReturnThis();
    });

    test('listForClass calls GET /enrollment/classes/{id}/students', async () => {
        axios.get.mockResolvedValue({ data: [] });
        await enrollmentApi.listForClass('class-1');
        expect(axios.get).toHaveBeenCalledWith('/enrollment/classes/class-1/students');
    });
});