#!/usr/bin/env node
// GitHub Repository Search Script
// Uses GitHub API to search for repositories based on keywords and filters

const https = require('https');
const url = require('url');

// Parse command line arguments
const args = process.argv.slice(2);
let query = '';
let maxResults = 10;
let language = '';
let sort = 'stars';
let dateFrom = '';
let outputFormat = 'table';

for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
        case '-q':
        case '--query':
            query = args[++i];
            break;
        case '-n':
        case '--max-results':
            maxResults = parseInt(args[++i], 10);
            break;
        case '-l':
        case '--language':
            language = args[++i];
            break;
        case '-s':
        case '--sort':
            sort = args[++i];
            break;
        case '--date-from':
            dateFrom = args[++i];
            break;
        case '--json':
            outputFormat = 'json';
            break;
        default:
            console.error(`Unknown option: ${args[i]}`);
            process.exit(1);
    }
}

if (!query) {
    console.error('Error: --query is required');
    console.error('Usage: node search_github.js -q "<query>" [-n max_results] [-l language] [-s sort] [--json]');
    process.exit(1);
}

// Build query string
let q = query;
if (language) q += ` language:${language}`;
if (dateFrom) q += ` pushed:>=${dateFrom}`;
q += ' stars:>=10';

// URL encode the query
const encodedQuery = encodeURIComponent(q);

// Build full URL
const apiUrl = `https://api.github.com/search/repositories?q=${encodedQuery}&sort=${sort}&per_page=${maxResults}`;

// Build request headers
const headers = {
    'User-Agent': 'GitHub-Search-Script'
};

if (process.env.GITHUB_TOKEN) {
    headers['Authorization'] = `token ${process.env.GITHUB_TOKEN}`;
}

// Make API request
const request = https.get(apiUrl, { headers, rejectUnauthorized: false }, (res) => {
    let data = '';

    res.on('data', (chunk) => {
        data += chunk;
    });

    res.on('end', () => {
        try {
            const jsonData = JSON.parse(data);

            if (jsonData.message) {
                console.error(`Error: ${jsonData.message}`);
                process.exit(1);
            }

            const items = jsonData.items || [];

            if (items.length === 0) {
                console.log('No results found.');
                process.exit(0);
            }

            if (outputFormat === 'json') {
                console.log(JSON.stringify(items, null, 2));
            } else {
                // Pretty print table format
                console.log('#    Project                                    Language    Stars     Forks    Updated     Description');
                console.log('-'.repeat(120));

                items.forEach((repo, i) => {
                    const name = repo.full_name || '';
                    const lang = repo.language || 'N/A';
                    const stars = repo.stargazers_count || 0;
                    const forks = repo.fork_count || 0;
                    const updated = (repo.updated_at || '').substring(0, 10);
                    let desc = repo.description || 'No description';
                    if (desc.length > 60) desc = desc.substring(0, 57) + '...';

                    // Format stars with K/M suffix
                    let starsStr;
                    if (stars >= 1000000) {
                        starsStr = `${(stars / 1000000).toFixed(1)}M`;
                    } else if (stars >= 1000) {
                        starsStr = `${(stars / 1000).toFixed(1)}k`;
                    } else {
                        starsStr = stars.toString();
                    }

                    console.log(`${(i + 1).toString().padEnd(4)} ${name.padEnd(40)} ${lang.padEnd(12)} ${starsStr.padEnd(10)} ${forks.toString().padEnd(8)} ${updated.padEnd(12)} ${desc}`);
                });
            }
        } catch (e) {
            console.error('Error parsing response:', e.message);
            process.exit(1);
        }
    });
});

request.on('error', (e) => {
    console.error('Request error:', e.message);
    process.exit(1);
});
