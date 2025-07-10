# options tracker

Checks daily options activity & notifies if there is anomolous volume that might indicate possible insider trading on a given ticker.The hypothesis is that people are cheating... so we're trying to see if anything jumps out that might prove it.


**Methodology**:

1) Scrape data from Yahoo Finance
2) Store data in local sqllite database. Note that only one day of data is available for free, so we need to build up our database by executing this daily over a period of time.
3) Check for anomolous behavior (excessive call/put, otm, short term expiration options) on each tracked stock (~1500).
4) Send email notification. Job is scheduled to run at market close each business day.


If this ends up being worthwhile I'll host the daily results/notifications somewhere publicly accessible.
