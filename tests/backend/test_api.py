"""
Tests for API endpoints
"""
import json
import pytest


class TestHealthEndpoint:
    """Tests for /api/health endpoint"""

    def test_health_check(self, client):
        """Test health check endpoint returns 200"""
        response = client.get('/api/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'ok'
        assert 'queue_size' in data
        assert 'current_job' in data
        assert 'total_completed' in data


class TestConfigEndpoints:
    """Tests for configuration endpoints"""

    def test_get_config(self, client):
        """Test GET /api/config returns configuration"""
        response = client.get('/api/config')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'model' in data
        assert 'generation' in data
        assert 'output' in data

    def test_update_config_missing_data(self, client):
        """Test PUT /api/config with missing data returns 400"""
        response = client.put('/api/config',
                             data=json.dumps({}),
                             content_type='application/json')
        assert response.status_code == 400

    def test_update_config_missing_required_keys(self, client):
        """Test PUT /api/config with missing required keys returns 400"""
        response = client.put('/api/config',
                             data=json.dumps({'model': {}}),
                             content_type='application/json')
        assert response.status_code == 400

    def test_update_config_path_traversal(self, client):
        """Test PUT /api/config blocks path traversal attempts"""
        config = {
            'model': {'default': 'test'},
            'generation': {'steps': 25},
            'output': {'directory': '../../../etc/passwd'}
        }
        response = client.put('/api/config',
                             data=json.dumps(config),
                             content_type='application/json')
        assert response.status_code == 400

    def test_update_generation_config(self, client):
        """Test PUT /api/config/generation updates generation settings"""
        updates = {'steps': 30, 'guidance_scale': 8.0}
        response = client.put('/api/config/generation',
                             data=json.dumps(updates),
                             content_type='application/json')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

    def test_update_generation_config_invalid_key(self, client):
        """Test PUT /api/config/generation rejects invalid keys"""
        updates = {'invalid_key': 'value'}
        response = client.put('/api/config/generation',
                             data=json.dumps(updates),
                             content_type='application/json')
        assert response.status_code == 400


class TestGenerateEndpoint:
    """Tests for /api/generate endpoint"""

    def test_generate_missing_prompt(self, client):
        """Test POST /api/generate without prompt returns 400"""
        response = client.post('/api/generate',
                              data=json.dumps({}),
                              content_type='application/json')
        assert response.status_code == 400

    def test_generate_empty_prompt(self, client):
        """Test POST /api/generate with empty prompt returns 400"""
        response = client.post('/api/generate',
                              data=json.dumps({'prompt': '   '}),
                              content_type='application/json')
        assert response.status_code == 400

    def test_generate_prompt_too_long(self, client):
        """Test POST /api/generate with overly long prompt returns 400"""
        long_prompt = 'a' * 2001  # Max is 2000
        response = client.post('/api/generate',
                              data=json.dumps({'prompt': long_prompt}),
                              content_type='application/json')
        assert response.status_code == 400

    def test_generate_valid_prompt(self, client, sample_job_data):
        """Test POST /api/generate with valid data returns 201 Created"""
        response = client.post('/api/generate',
                              data=json.dumps(sample_job_data),
                              content_type='application/json')
        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'id' in data
        assert data['status'] == 'queued'
        assert data['prompt'] == sample_job_data['prompt']
        assert 'queue_position' in data
        assert 'Location' in response.headers
        assert f"/api/jobs/{data['id']}" in response.headers['Location']

    def test_generate_invalid_seed(self, client):
        """Test POST /api/generate with invalid seed returns 400"""
        test_cases = [
            {'prompt': 'test', 'seed': -1},  # Negative
            {'prompt': 'test', 'seed': 2147483648},  # Too large
            {'prompt': 'test', 'seed': 'invalid'},  # String
        ]
        for data in test_cases:
            response = client.post('/api/generate',
                                  data=json.dumps(data),
                                  content_type='application/json')
            assert response.status_code == 400

    def test_generate_invalid_steps(self, client):
        """Test POST /api/generate with invalid steps returns 400"""
        test_cases = [
            {'prompt': 'test', 'steps': 0},  # Too low
            {'prompt': 'test', 'steps': 151},  # Too high
            {'prompt': 'test', 'steps': 'invalid'},  # String
        ]
        for data in test_cases:
            response = client.post('/api/generate',
                                  data=json.dumps(data),
                                  content_type='application/json')
            assert response.status_code == 400

    def test_generate_invalid_dimensions(self, client):
        """Test POST /api/generate with invalid width/height returns 400"""
        test_cases = [
            {'prompt': 'test', 'width': 63},  # Too small
            {'prompt': 'test', 'width': 2049},  # Too large
            {'prompt': 'test', 'width': 511},  # Not divisible by 8
            {'prompt': 'test', 'height': 63},  # Too small
            {'prompt': 'test', 'height': 2049},  # Too large
            {'prompt': 'test', 'height': 511},  # Not divisible by 8
        ]
        for data in test_cases:
            response = client.post('/api/generate',
                                  data=json.dumps(data),
                                  content_type='application/json')
            assert response.status_code == 400

    def test_generate_invalid_guidance_scale(self, client):
        """Test POST /api/generate with invalid guidance_scale returns 400"""
        test_cases = [
            {'prompt': 'test', 'guidance_scale': -1},  # Negative
            {'prompt': 'test', 'guidance_scale': 31},  # Too high
            {'prompt': 'test', 'guidance_scale': 'invalid'},  # String
        ]
        for data in test_cases:
            response = client.post('/api/generate',
                                  data=json.dumps(data),
                                  content_type='application/json')
            assert response.status_code == 400


class TestJobsEndpoints:
    """Tests for job management endpoints"""

    def test_get_jobs(self, client):
        """Test GET /api/jobs returns job lists"""
        response = client.get('/api/jobs')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'current' in data
        assert 'queued' in data
        assert 'history' in data

    def test_get_nonexistent_job(self, client):
        """Test GET /api/jobs/{id} for nonexistent job returns 404"""
        response = client.get('/api/jobs/99999')
        assert response.status_code == 404


class TestOutputsEndpoints:
    """Tests for output/image endpoints"""

    def test_list_outputs(self, client):
        """Test GET /api/outputs returns image list"""
        response = client.get('/api/outputs')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'images' in data

    def test_serve_nonexistent_file(self, client):
        """Test GET /api/outputs/{filename} for nonexistent file returns 404"""
        response = client.get('/api/outputs/nonexistent.png')
        assert response.status_code == 404

    def test_serve_path_traversal_blocked(self, client):
        """Test path traversal attempts are blocked"""
        # Try various path traversal attempts
        test_paths = [
            '../../../etc/passwd',
            '..%2F..%2F..%2Fetc%2Fpasswd',
            'subdir/../../etc/passwd',
        ]
        for path in test_paths:
            response = client.get(f'/api/outputs/{path}')
            # Should return either 403 (access denied) or 404 (not found after sanitization)
            assert response.status_code in [403, 404]
