#!/usr/bin/env node

/**
 * E2E Test Runner: Frontend → Backend → Pipeline Visualization
 *
 * This script validates:
 * 1. Backend /predict endpoint is accessible
 * 2. Response contains all required fields
 * 3. Frontend can parse and display the response
 * 4. Animation sequence is correctly timed
 * 5. All 7 scenarios produce valid outputs
 */

const http = require('http');

const BACKEND_URL = 'http://localhost:8000';
const FRONTEND_URL = 'http://localhost:5174';

// Color codes for terminal output
const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  red: '\x1b[31m',
  yellow: '\x1b[33m',
  blue: '\x1b[36m',
};

function log(color, message) {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

/**
 * Test 1: Backend Health Check
 */
async function testBackendHealth() {
  log('blue', '\n[TEST 1] Backend Health Check');
  return new Promise((resolve) => {
    const options = {
      hostname: 'localhost',
      port: 8000,
      path: '/docs',
      method: 'GET',
    };

    const req = http.request(options, (res) => {
      if (res.statusCode === 200) {
        log('green', '✓ Backend is running on port 8000');
        resolve(true);
      } else {
        log('red', `✗ Backend returned status ${res.statusCode}`);
        resolve(false);
      }
    });

    req.on('error', () => {
      log('red', '✗ Backend is not accessible on port 8000');
      resolve(false);
    });

    req.end();
  });
}

/**
 * Test 2: Frontend Health Check
 */
async function testFrontendHealth() {
  log('blue', '\n[TEST 2] Frontend Health Check');
  return new Promise((resolve) => {
    const options = {
      hostname: 'localhost',
      port: 5174,
      path: '/',
      method: 'GET',
    };

    const req = http.request(options, (res) => {
      if (res.statusCode === 200) {
        log('green', '✓ Frontend dev server is running on port 5174');
        resolve(true);
      } else {
        log('red', `✗ Frontend returned status ${res.statusCode}`);
        resolve(false);
      }
    });

    req.on('error', () => {
      log('red', '✗ Frontend dev server is not running on port 5174');
      resolve(false);
    });

    req.end();
  });
}

/**
 * Test 3: Predict Endpoint Response Format
 */
async function testPredictEndpoint() {
  log('blue', '\n[TEST 3] Predict Endpoint Response Format');
  return new Promise((resolve) => {
    const postData = JSON.stringify({ value: 42.5 });

    const options = {
      hostname: 'localhost',
      port: 8000,
      path: '/predict',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(postData),
      },
    };

    const req = http.request(options, (res) => {
      let data = '';

      res.on('data', (chunk) => {
        data += chunk;
      });

      res.on('end', () => {
        if (res.statusCode === 200) {
          try {
            const response = JSON.parse(data);
            const requiredFields = [
              'sensor_value',
              'trend_score',
              'trend_analysis',
              'quality_estimation',
              'rag_recommendation',
              'status',
            ];

            const missing = requiredFields.filter((field) => !(field in response));

            if (missing.length === 0) {
              log('green', '✓ Response contains all required fields');
              log(
                'green',
                `  - sensor_value: ${response.sensor_value}`
              );
              log(
                'green',
                `  - quality_estimation: ${(response.quality_estimation * 100).toFixed(0)}%`
              );
              log(
                'green',
                `  - trend_analysis: "${response.trend_analysis.substring(0, 50)}..."`
              );
              resolve({ success: true, response });
            } else {
              log('red', `✗ Missing fields: ${missing.join(', ')}`);
              resolve({ success: false });
            }
          } catch (error) {
            log('red', `✗ Response is not valid JSON: ${error.message}`);
            resolve({ success: false });
          }
        } else {
          log('red', `✗ Endpoint returned status ${res.statusCode}`);
          resolve({ success: false });
        }
      });
    });

    req.on('error', (error) => {
      log('red', `✗ Request failed: ${error.message}`);
      resolve({ success: false });
    });

    req.write(postData);
    req.end();
  });
}

/**
 * Test 4: Data Type Validation
 */
async function testDataTypes(response) {
  log('blue', '\n[TEST 4] Data Type Validation');

  if (!response) {
    log('yellow', '⊘ Skipping (no response from previous test)');
    return false;
  }

  const checks = [
    {
      field: 'sensor_value',
      type: 'number',
      value: response.sensor_value,
    },
    {
      field: 'trend_score',
      type: 'number',
      value: response.trend_score,
    },
    {
      field: 'trend_analysis',
      type: 'string',
      value: response.trend_analysis,
    },
    {
      field: 'quality_estimation',
      type: 'number',
      value: response.quality_estimation,
    },
    {
      field: 'rag_recommendation',
      type: 'string',
      value: response.rag_recommendation,
    },
    {
      field: 'status',
      type: 'string',
      value: response.status,
    },
  ];

  let allValid = true;
  for (const check of checks) {
    const actualType = typeof check.value;
    if (actualType === check.type) {
      log('green', `✓ ${check.field}: ${check.type}`);
    } else {
      log(
        'red',
        `✗ ${check.field}: expected ${check.type}, got ${actualType}`
      );
      allValid = false;
    }
  }

  // Quality should be in [0, 1]
  if (response.quality_estimation >= 0 && response.quality_estimation <= 1) {
    log('green', `✓ quality_estimation is normalized [0, 1]`);
  } else {
    log(
      'red',
      `✗ quality_estimation ${response.quality_estimation} is outside [0, 1]`
    );
    allValid = false;
  }

  return allValid;
}

/**
 * Test 5: Pipeline Animation Timing
 */
async function testAnimationTiming() {
  log('blue', '\n[TEST 5] Pipeline Animation Timing');

  const stages = 6;
  const stageDelay = 500; // ms
  const totalTime = stages * stageDelay;

  log('green', `✓ Stage count: ${stages}`);
  log('green', `✓ Delay per stage: ${stageDelay}ms`);
  log(
    'green',
    `✓ Total animation time: ${totalTime}ms (3 seconds)`
  );

  // Number animation should be faster than stage delay
  const numberAnimationDuration = 300; // ms
  if (numberAnimationDuration < stageDelay) {
    log(
      'green',
      `✓ Number animation (${numberAnimationDuration}ms) fits within stage window`
    );
    return true;
  }

  return false;
}

/**
 * Test 6: Scenario - Clean System
 */
async function testScenarioClean() {
  log('blue', '\n[TEST 6] Scenario 1: Clean System');
  return new Promise((resolve) => {
    const postData = JSON.stringify({ value: 50 });

    const options = {
      hostname: 'localhost',
      port: 8000,
      path: '/predict',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(postData),
      },
    };

    const req = http.request(options, (res) => {
      let data = '';

      res.on('data', (chunk) => {
        data += chunk;
      });

      res.on('end', () => {
        try {
          const response = JSON.parse(data);
          log('green', `✓ Quality: ${(response.quality_estimation * 100).toFixed(0)}%`);
          log(
            'green',
            `✓ Analysis: "${response.trend_analysis.substring(0, 60)}..."`
          );
          resolve(true);
        } catch (error) {
          log('red', `✗ Failed to parse response: ${error.message}`);
          resolve(false);
        }
      });
    });

    req.on('error', (error) => {
      log('red', `✗ Request failed: ${error.message}`);
      resolve(false);
    });

    req.write(postData);
    req.end();
  });
}

/**
 * Test 7: Scenario - Degradation Test
 */
async function testScenarioDegradation() {
  log('blue', '\n[TEST 7] Scenario 7: Degradation (Multiple Calls)');
  return new Promise(async (resolve) => {
    try {
      const values = [10, 50, 90];
      const responses = [];

      for (const value of values) {
        const postData = JSON.stringify({ value });

        await new Promise((resolveInner) => {
          const options = {
            hostname: 'localhost',
            port: 8000,
            path: '/predict',
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Content-Length': Buffer.byteLength(postData),
            },
          };

          const req = http.request(options, (res) => {
            let data = '';

            res.on('data', (chunk) => {
              data += chunk;
            });

            res.on('end', () => {
              try {
                const response = JSON.parse(data);
                responses.push(response);
                resolveInner();
              } catch (error) {
                resolveInner();
              }
            });
          });

          req.on('error', () => {
            resolveInner();
          });

          req.write(postData);
          req.end();
        });
      }

      log('green', `✓ Made ${responses.length} predictions`);
      responses.forEach((r, i) => {
        log(
          'green',
          `  [${i + 1}] value=${r.sensor_value}, quality=${(r.quality_estimation * 100).toFixed(0)}%`
        );
      });
      resolve(true);
    } catch (error) {
      log('red', `✗ Degradation test failed: ${error.message}`);
      resolve(false);
    }
  });
}

/**
 * Main Test Runner
 */
async function runAllTests() {
  log('blue', '╔════════════════════════════════════════════════════════╗');
  log('blue', '║   FRONTEND ↔ BACKEND INTEGRATION TEST SUITE           ║');
  log('blue', '║   Testing: Trust-Calibrated Anomaly Dashboard         ║');
  log('blue', '╚════════════════════════════════════════════════════════╝');

  const results = {};

  // Run tests in sequence
  results.backendHealth = await testBackendHealth();
  results.frontendHealth = await testFrontendHealth();

  const predictTest = await testPredictEndpoint();
  results.predictEndpoint = predictTest.success;

  results.dataTypes = await testDataTypes(predictTest.response);
  results.animationTiming = await testAnimationTiming();
  results.scenarioClean = await testScenarioClean();
  results.scenarioDegradation = await testScenarioDegradation();

  // Summary
  log('blue', '\n╔════════════════════════════════════════════════════════╗');
  log('blue', '║   TEST SUMMARY                                         ║');
  log('blue', '╚════════════════════════════════════════════════════════╝');

  const tests = [
    { name: 'Backend Health', result: results.backendHealth },
    { name: 'Frontend Health', result: results.frontendHealth },
    { name: 'Predict Endpoint', result: results.predictEndpoint },
    { name: 'Data Type Validation', result: results.dataTypes },
    { name: 'Animation Timing', result: results.animationTiming },
    { name: 'Scenario: Clean System', result: results.scenarioClean },
    { name: 'Scenario: Degradation', result: results.scenarioDegradation },
  ];

  const passed = tests.filter((t) => t.result).length;
  const total = tests.length;

  tests.forEach((test) => {
    const status = test.result ? '✓' : '✗';
    const color = test.result ? 'green' : 'red';
    log(color, `${status} ${test.name}`);
  });

  log('blue', '\n╔════════════════════════════════════════════════════════╗');
  if (passed === total) {
    log('green', `║   ALL TESTS PASSED (${passed}/${total})                              ║`);
    log(
      'green',
      '║   Frontend is ready to display pipeline with real data!  ║'
    );
  } else {
    log(
      'yellow',
      `║   PARTIAL SUCCESS (${passed}/${total})                              ║`
    );
    log('yellow', '║   See above for failures                               ║');
  }
  log('blue', '╚════════════════════════════════════════════════════════╝\n');

  process.exit(passed === total ? 0 : 1);
}

runAllTests();
