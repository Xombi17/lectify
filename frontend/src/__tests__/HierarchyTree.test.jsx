import { vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import HierarchyTree from '../components/HierarchyTree';

// Mock the admin API
vi.mock('../lib/api', () => {
    const empty = () => vi.fn().mockResolvedValue([]);
    return {
        adminApi: {
            listInstitutions: vi.fn().mockResolvedValue([
                { id: 'i1', name: 'Test Institution', code: 'TI' }
            ]),
            listYears: empty(),
            listSemesters: empty(),
            listSubjects: empty(),
            listDivisions: empty(),
            listClasses: empty(),
            listBranches: empty(),
            listBatches: empty(),
            listInstitutionYears: empty(),
            listInstitutionBranches: empty(),
            listInstitutionBatches: empty(),
        },
    };
});

describe('HierarchyTree', () => {
    test('renders loading state initially', () => {
        render(<HierarchyTree />);
        // Should show loading indicator
        expect(screen.getByTestId('hierarchy-tree')).toBeInTheDocument();
    });

    test('renders institution nodes after loading', async () => {
        render(<HierarchyTree />);
        await waitFor(() => {
            expect(screen.getAllByText('Test Institution').length).toBeGreaterThan(0);
        });
    });

    test('calls listInstitutions on mount', async () => {
        const { adminApi } = await import('../lib/api');
        render(<HierarchyTree />);
        await waitFor(() => {
            expect(adminApi.listInstitutions).toHaveBeenCalled();
        });
    });
});