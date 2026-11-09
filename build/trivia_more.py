"""Other > Trivia: a much bigger question bank, and rounds that favour questions this phone has not seen.

Christopher, 17 Oct 2026: "add a lot more trivia".  Same rules as the first 48 (16 Oct 2026): NHL only, settled
history only (records, awards, Cup winners to 2025, drafts to 2025, franchise moves), so nothing goes stale with
the season.  Each entry is [question, right answer, three wrong answers, the fact shown after].

Rounds now draw questions this phone has not seen first (kept as polska-trivseen), and start over once all have
been seen.

    python build/trivia_more.py index.html
Safe to run again; keeps the file's own line endings.
"""
import sys

MARK = "/* trivia_more.py: */"

ANCHOR = '''    ["In what year did Los Angeles win its first Stanley Cup?","2012",["1993","2010","2014"],"The Kings won again two years later, in 2014."],
  ];'''

NEW = [
    # records
    ["How many goals did Reggie Leach score in the 1976 playoffs, still the record for one playoff year?", "19", ["15", "17", "21"], "Jari Kurri matched it with Edmonton in 1985."],
    ["Who holds the record for points in one playoff year?", "Wayne Gretzky", ["Mario Lemieux", "Connor McDavid", "Mark Messier"], "Gretzky had 47 points in the 1985 playoffs. McDavid came close with 42 in 2024."],
    ["Who has the most career playoff points?", "Wayne Gretzky", ["Mark Messier", "Jari Kurri", "Glenn Anderson"], "Gretzky had 382 playoff points, including a record 122 goals."],
    ["Who has the most career assists?", "Wayne Gretzky", ["Ron Francis", "Mark Messier", "Ray Bourque"], "Gretzky had 1,963 assists. Ron Francis is second with 1,249."],
    ["Who holds the record for most NHL games played?", "Patrick Marleau", ["Gordie Howe", "Mark Messier", "Joe Thornton"], "Marleau passed Gordie Howe's 1,767 games in 2021 and finished with 1,779."],
    ["Which defenceman scored the most career goals?", "Ray Bourque", ["Paul Coffey", "Al MacInnis", "Phil Housley"], "Bourque scored 410. Paul Coffey is next with 396."],
    ["Who holds the record for points in a season by a defenceman?", "Bobby Orr", ["Paul Coffey", "Erik Karlsson", "Cale Makar"], "Orr had 139 points in 1970-71. Coffey came one short with 138 in 1985-86."],
    ["Which defenceman holds the record for goals in a season?", "Paul Coffey", ["Bobby Orr", "Al MacInnis", "Mike Green"], "Coffey scored 48 for Edmonton in 1985-86, two more than Orr's best of 46."],
    ["What is the record for goals by one player in a single NHL game?", "7", ["5", "6", "8"], "Joe Malone scored seven for the Quebec Bulldogs in 1920."],
    ["Who scored the fastest hat trick in NHL history, three goals in 21 seconds?", "Bill Mosienko", ["Jean Beliveau", "Maurice Richard", "Bobby Hull"], "Mosienko did it for Chicago on March 23, 1952."],
    ["Mike Bossy scored 50 or more goals in how many straight seasons to start his career?", "9", ["6", "7", "8"], "He did it every year from 1977-78 to 1985-86 with the Islanders."],
    ["Who has the most career hat tricks?", "Wayne Gretzky", ["Mario Lemieux", "Mike Bossy", "Brett Hull"], "Gretzky had 50. Lemieux had 40 and Bossy 39."],
    ["How many goals did Brett Hull score for St. Louis in 1990-91?", "86", ["72", "79", "92"], "Only Gretzky, with 92 and 87, has scored more in a season."],
    ["How many goals did Auston Matthews score in 2023-24?", "69", ["60", "64", "70"], "It matched Mario Lemieux's 69 in 1995-96, the most in a season since then."],
    ["Which defenceman had 102 assists in 1970-71?", "Bobby Orr", ["Paul Coffey", "Denis Potvin", "Brad Park"], "Orr is still the only defenceman with 100 assists in a season."],
    ["How many Art Ross Trophies did Wayne Gretzky win as the league's top scorer?", "10", ["7", "8", "9"], "Mario Lemieux and Gordie Howe are next with six each."],
    ["How many Hart Trophies did Wayne Gretzky win?", "9", ["6", "7", "8"], "Eight in a row from 1980 to 1987, then one more in 1989."],
    ["Who won the Norris Trophy as the best defenceman a record eight times?", "Bobby Orr", ["Doug Harvey", "Nicklas Lidstrom", "Ray Bourque"], "Orr won it eight years in a row, 1968 to 1975. Harvey and Lidstrom won seven each."],
    ["Which goalie won the Vezina Trophy a record seven times?", "Jacques Plante", ["Dominik Hasek", "Patrick Roy", "Martin Brodeur"], "Plante won most of them with Montreal in the 1950s."],
    ["Which goalie has the most playoff wins?", "Patrick Roy", ["Martin Brodeur", "Andrei Vasilevskiy", "Grant Fuhr"], "Roy won 151 playoff games with Montreal and Colorado."],
    ["Who scored the most career playoff goals?", "Wayne Gretzky", ["Mark Messier", "Jari Kurri", "Brett Hull"], "Gretzky scored 122 playoff goals."],
    ["Who played the most playoff games in NHL history?", "Chris Chelios", ["Nicklas Lidstrom", "Patrick Roy", "Mark Messier"], "Chelios played 266 playoff games over 26 seasons."],
    ["Which team holds the record unbeaten streak of 35 games, set in 1979-80?", "Philadelphia Flyers", ["Montreal Canadiens", "Pittsburgh Penguins", "Boston Bruins"], "The Flyers went 25 wins and 10 ties without a loss."],
    ["Which team holds the record of 17 straight wins, set in 1992-93?", "Pittsburgh Penguins", ["Columbus Blue Jackets", "Detroit Red Wings", "Washington Capitals"], "Columbus came closest with 16 in a row in 2016-17."],
    ["Which team set the records for wins (65) and points (135) in a season in 2022-23?", "Boston Bruins", ["Tampa Bay Lightning", "Colorado Avalanche", "Carolina Hurricanes"], "They lost in the first round to Florida."],
    ["Tampa Bay tied the wins record with 62 in 2018-19. Who swept them in the first round?", "Columbus Blue Jackets", ["Boston Bruins", "Toronto Maple Leafs", "Washington Capitals"], "It was Columbus's first playoff series win ever."],
    ["The longest game in NHL history, in 1936, went how many overtimes?", "6", ["4", "5", "7"], "Mud Bruneteau scored for Detroit after 116 minutes 30 seconds of overtime against the Montreal Maroons."],
    ["Who was the first goalie credited with scoring a goal by shooting the puck into the net?", "Ron Hextall", ["Martin Brodeur", "Billy Smith", "Chris Osgood"], "Hextall did it for Philadelphia against Boston in December 1987."],
    ["Mario Lemieux once scored five goals in a game in five different ways. Against which team?", "New Jersey Devils", ["New York Rangers", "Philadelphia Flyers", "Boston Bruins"], "Even strength, power play, short-handed, penalty shot and empty net, on Dec 31, 1988."],
    ["How many 50-goal seasons did Alex Ovechkin have, tied for the record?", "9", ["7", "8", "10"], "He shares the record with Wayne Gretzky and Mike Bossy."],
    # awards
    ["Who votes for the Hart Trophy as league MVP?", "Hockey writers", ["The players", "The general managers", "The coaches"], "The Professional Hockey Writers' Association votes on it."],
    ["Who votes for the Ted Lindsay Award?", "The players", ["Hockey writers", "The general managers", "The fans"], "It was called the Lester B. Pearson Award until 2010."],
    ["Who votes for the Vezina Trophy?", "The general managers", ["Hockey writers", "The players", "The coaches"], "The 32 GMs pick the best goalie."],
    ["The Jack Adams Award goes to whom?", "The coach of the year", ["The best defenceman", "The playoff MVP", "The general manager of the year"], "It is named for the longtime Detroit coach and GM."],
    ["The Lady Byng Trophy rewards what?", "Sportsmanship and skill", ["Leadership", "Defensive play", "Perseverance"], "Frank Boucher won it seven times and was given the original trophy to keep."],
    ["What does a team win for the best regular-season record?", "The Presidents' Trophy", ["The Prince of Wales Trophy", "The Clarence Campbell Bowl", "The King Clancy Trophy"], "It was first awarded in 1985-86."],
    ["The Clarence S. Campbell Bowl goes to which team?", "The Western Conference playoff champion", ["The best regular-season team", "The Eastern Conference playoff champion", "The team with the fewest penalties"], "The Prince of Wales Trophy goes to the Eastern champion."],
    ["Who won the first Rocket Richard Trophy for most goals, in 1998-99?", "Teemu Selanne", ["Jaromir Jagr", "Pavel Bure", "Peter Bondra"], "Selanne scored 47 for Anaheim."],
    ["The Bill Masterton Trophy rewards what?", "Perseverance and dedication to hockey", ["The most goals in a season", "The best rookie goalie", "Community service"], "Masterton is the only player to die from an injury suffered in an NHL game, in 1968."],
    ["The William M. Jennings Trophy goes to whom?", "The goalies on the team allowing the fewest goals", ["The best rookie", "The top scorer", "The most improved player"], "Unlike the Vezina, it is decided by the numbers, not a vote."],
    ["Who won the very first Conn Smythe Trophy, in 1965?", "Jean Beliveau", ["Gordie Howe", "Bobby Hull", "Johnny Bower"], "Beliveau led Montreal past Chicago in the Final."],
    ["Which goalie won the Conn Smythe in 1987 even though Philadelphia lost the Final?", "Ron Hextall", ["Grant Fuhr", "Pelle Lindbergh", "Patrick Roy"], "Edmonton won that Final in seven games."],
    ["Who won the Conn Smythe in 2003 even though Anaheim lost the Final?", "Jean-Sebastien Giguere", ["Martin Brodeur", "Paul Kariya", "Scott Niedermayer"], "New Jersey won the Cup in seven games."],
    ["Which goalie won the Conn Smythe in 1971, a year before he won the Calder Trophy as top rookie?", "Ken Dryden", ["Tony Esposito", "Bernie Parent", "Gerry Cheevers"], "He had played only six regular-season games before that playoff run."],
    ["Bobby and Brett Hull are the only father and son to both win which award?", "The Hart Trophy", ["The Art Ross Trophy", "The Conn Smythe Trophy", "The Calder Trophy"], "Bobby won it in 1965 and 1966, Brett in 1991."],
    ["Which goalie is the only one to win the Hart Trophy twice?", "Dominik Hasek", ["Patrick Roy", "Jacques Plante", "Carey Price"], "Hasek won it in 1997 and 1998 with Buffalo."],
    ["In 2015 Carey Price won the Hart Trophy and which other award as the best goalie?", "The Vezina Trophy", ["The Conn Smythe Trophy", "The Calder Trophy", "The Selke Trophy"], "He also won the Ted Lindsay Award and the Jennings Trophy that year."],
    ["Who won the Conn Smythe Trophy in 2022?", "Cale Makar", ["Nathan MacKinnon", "Andrei Vasilevskiy", "Mikko Rantanen"], "Makar also won the Norris Trophy that season."],
    ["Who won the Conn Smythe Trophy in 2023?", "Jonathan Marchessault", ["Jack Eichel", "Adin Hill", "Matthew Tkachuk"], "Marchessault was an original Golden Knight, taken in the 2017 expansion draft."],
    ["Who won the Conn Smythe Trophy in 2025?", "Sam Bennett", ["Matthew Tkachuk", "Sergei Bobrovsky", "Aleksander Barkov"], "Bennett scored 15 goals in that playoff run."],
    ["Who won the Conn Smythe Trophy in 2020?", "Victor Hedman", ["Nikita Kucherov", "Brayden Point", "Andrei Vasilevskiy"], "Tampa Bay beat Dallas in the Edmonton bubble."],
    ["Who won the Conn Smythe Trophy in 2019?", "Ryan O'Reilly", ["Jordan Binnington", "Vladimir Tarasenko", "Alex Pietrangelo"], "O'Reilly also won the Selke Trophy that season."],
    ["Who won the Conn Smythe Trophy in 2021?", "Andrei Vasilevskiy", ["Nikita Kucherov", "Victor Hedman", "Brayden Point"], "He finished the Final with a shutout in Game 5 against Montreal."],
    ["Henrik and Daniel Sedin won the Art Ross Trophy in back-to-back years. Which came first?", "Henrik, 2010", ["Daniel, 2010", "Henrik, 2011", "Daniel, 2009"], "Daniel won it the next year, 2011. Both twins retired from Vancouver in 2018."],
    ["Joe Thornton won the Art Ross and Hart Trophies in 2005-06 after being traded mid-season. To which team?", "San Jose Sharks", ["Boston Bruins", "Toronto Maple Leafs", "Ottawa Senators"], "Boston traded him to San Jose that November."],
    ["How old was Sidney Crosby when he won his first Art Ross Trophy in 2007?", "19", ["18", "20", "21"], "He was the youngest scoring champion in a major North American sport."],
    # Stanley Cup history
    ["Which team won four straight Stanley Cups from 1980 to 1983?", "New York Islanders", ["Edmonton Oilers", "Montreal Canadiens", "Philadelphia Flyers"], "The Islanders also won a record 19 straight playoff series."],
    ["The record for consecutive Stanley Cups is five. Which team did it?", "Montreal Canadiens", ["Toronto Maple Leafs", "New York Islanders", "Detroit Red Wings"], "Montreal won every year from 1956 to 1960."],
    ["Philadelphia's 'Broad Street Bullies' won the Cup in which two years?", "1974 and 1975", ["1973 and 1974", "1975 and 1976", "1976 and 1977"], "They were the first expansion team to win the Cup."],
    ["Tampa Bay won its first Stanley Cup in 2004 by beating whom?", "Calgary Flames", ["Vancouver Canucks", "Edmonton Oilers", "Ottawa Senators"], "Tampa Bay won Game 7 at home, 2-1."],
    ["Who won the Stanley Cup in 2006, beating Edmonton in seven games?", "Carolina Hurricanes", ["Anaheim Ducks", "Tampa Bay Lightning", "Buffalo Sabres"], "Rookie goalie Cam Ward won the Conn Smythe."],
    ["Anaheim won its only Stanley Cup in 2007 by beating which team?", "Ottawa Senators", ["Detroit Red Wings", "Buffalo Sabres", "New Jersey Devils"], "Scott Niedermayer won the Conn Smythe."],
    ["How many Stanley Cups did Chicago win from 2010 to 2015?", "3", ["2", "4", "1"], "2010, 2013 and 2015. The 2010 Cup ended a drought going back to 1961."],
    ["Who scored the overtime goal that won the 2010 Cup for Chicago?", "Patrick Kane", ["Jonathan Toews", "Marian Hossa", "Patrick Sharp"], "Few people in the building saw it go in at first, in Philadelphia."],
    ["Boston won the Cup in 2011, its first since 1972. Who did they beat?", "Vancouver Canucks", ["Philadelphia Flyers", "Tampa Bay Lightning", "San Jose Sharks"], "Tim Thomas won the Conn Smythe."],
    ["Washington won its first Stanley Cup in 2018. Who did they beat?", "Vegas Golden Knights", ["Pittsburgh Penguins", "Tampa Bay Lightning", "Winnipeg Jets"], "Alex Ovechkin won the Conn Smythe."],
    ["Where was the 2020 Stanley Cup Final played?", "Edmonton", ["Toronto", "Las Vegas", "Chicago"], "The playoffs were held in bubbles in Toronto and Edmonton; Tampa Bay beat Dallas."],
    ["Who did Tampa Bay beat in the 2021 Final?", "Montreal Canadiens", ["Dallas Stars", "Vegas Golden Knights", "New York Islanders"], "It made Tampa Bay back-to-back champions."],
    ["Who scored the double-overtime goal that won the 2014 Cup for Los Angeles?", "Alec Martinez", ["Justin Williams", "Anze Kopitar", "Jeff Carter"], "The Kings beat the Rangers in five games."],
    ["Los Angeles won its first Cup in 2012 by beating which team?", "New Jersey Devils", ["New York Rangers", "Philadelphia Flyers", "Boston Bruins"], "Goalie Jonathan Quick won the Conn Smythe."],
    ["Pittsburgh beat Detroit in Game 7 of the 2009 Final. Who scored both Pittsburgh goals?", "Max Talbot", ["Sidney Crosby", "Evgeni Malkin", "Jordan Staal"], "Pittsburgh won 2-1 in Detroit."],
    ["Detroit won the 2008 Cup over Pittsburgh. Who won the Conn Smythe?", "Henrik Zetterberg", ["Nicklas Lidstrom", "Pavel Datsyuk", "Chris Osgood"], "The teams met again in the Final a year later."],
    ["Brett Hull's famous triple-overtime goal won the 1999 Cup for which team?", "Dallas Stars", ["St. Louis Blues", "Detroit Red Wings", "Buffalo Sabres"], "Buffalo fans still argue his skate was in the crease."],
    ["Colorado won the Cup in its first season after moving from Quebec. Which year?", "1996", ["1995", "1997", "2001"], "They swept Florida, ending it on Uwe Krupp's triple-overtime goal."],
    ["How many Stanley Cups did New Jersey win?", "3", ["1", "2", "4"], "1995, 2000 and 2003, all with Martin Brodeur in goal."],
    ["Detroit's 1997 Cup ended a drought going back to which year?", "1955", ["1950", "1966", "1972"], "Steve Yzerman's Red Wings swept Philadelphia."],
    ["The 1919 Stanley Cup Final was never finished. Why?", "A flu pandemic", ["A players' strike", "A fire at the arena", "A war"], "Montreal and the Seattle Metropolitans were tied when it was cancelled."],
    ["Which was the first American team to win the Stanley Cup, in 1917?", "Seattle Metropolitans", ["Boston Bruins", "New York Rangers", "Detroit Cougars"], "They beat the Montreal Canadiens."],
    ["In which year was the Stanley Cup first awarded?", "1893", ["1875", "1910", "1917"], "It went to the Montreal Hockey Club, before the NHL existed."],
    ["Why was no Stanley Cup awarded in 2005?", "The season was cancelled by a lockout", ["A pandemic", "The Final was never finished", "The Cup was stolen"], "The NHL was the first major North American league to lose a full season."],
    ["St. Louis reached the Final in each of its first three seasons. How did those Finals go?", "Swept all three times", ["Won one", "Won two", "Lost each in seven games"], "The Blues finally won the Cup in 2019."],
    ["Who scored the 1964 Cup Final overtime winner while playing on a broken leg?", "Bobby Baun", ["Tim Horton", "Dave Keon", "Frank Mahovlich"], "He scored for Toronto in Game 6 against Detroit."],
    ["Bill Barilko won the 1951 Cup for Toronto in overtime, then vanished in a plane crash. When did Toronto next win?", "1962", ["1952", "1955", "1967"], "The wreckage of the plane was found later that same year."],
    ["How many days does each player on the winning team get to spend with the Stanley Cup?", "One day", ["One week", "One hour", "None"], "The Cup travels with a keeper from the Hockey Hall of Fame."],
    ["Montreal won the 1993 Cup after which LA player was caught with an illegal stick curve?", "Marty McSorley", ["Wayne Gretzky", "Luc Robitaille", "Rob Blake"], "Montreal tied the game on the power play and won in overtime."],
    # teams
    ["How many teams joined the NHL in the 1967 expansion?", "6", ["2", "4", "8"], "Los Angeles, Minnesota, Oakland, Philadelphia, Pittsburgh and St. Louis doubled the league."],
    ["Which of these did NOT come into the NHL from the WHA in 1979?", "Calgary Flames", ["Edmonton Oilers", "Hartford Whalers", "Quebec Nordiques"], "The Flames moved from Atlanta in 1980. Winnipeg was the fourth WHA team."],
    ["The Hartford Whalers moved and became which team in 1997?", "Carolina Hurricanes", ["Columbus Blue Jackets", "Nashville Predators", "Dallas Stars"], "Carolina won the Cup in 2006."],
    ["The Quebec Nordiques moved in 1995 and became which team?", "Colorado Avalanche", ["Dallas Stars", "Phoenix Coyotes", "Carolina Hurricanes"], "Colorado won the Cup in its first season."],
    ["The original Winnipeg Jets moved in 1996 and became which team?", "Phoenix Coyotes", ["Colorado Avalanche", "Dallas Stars", "Minnesota Wild"], "Winnipeg got a team back in 2011 when Atlanta moved there."],
    ["The current Winnipeg Jets moved from which city in 2011?", "Atlanta", ["Phoenix", "Hartford", "Quebec City"], "They were the Atlanta Thrashers."],
    ["The Minnesota North Stars moved in 1993 and became which team?", "Dallas Stars", ["Colorado Avalanche", "Carolina Hurricanes", "Arizona Coyotes"], "Minnesota got the Wild in 2000."],
    ["The New Jersey Devils started out in 1974 as which team?", "Kansas City Scouts", ["Colorado Rockies", "Cleveland Barons", "California Golden Seals"], "Kansas City moved to Colorado in 1976, then to New Jersey in 1982."],
    ["Which two teams joined the NHL in 1993?", "Anaheim and Florida", ["Tampa Bay and Ottawa", "Nashville and Atlanta", "Columbus and Minnesota"], "Anaheim began as the Mighty Ducks, named for the Disney movie."],
    ["Which team joined the NHL in 2000 along with Columbus?", "Minnesota Wild", ["Atlanta Thrashers", "Nashville Predators", "San Jose Sharks"], "Nashville came in 1998 and Atlanta in 1999."],
    ["Which two teams joined the NHL in 1992?", "Ottawa and Tampa Bay", ["Anaheim and Florida", "San Jose and Ottawa", "Florida and Tampa Bay"], "San Jose had joined a year earlier, in 1991."],
    ["Florida fans throw what on the ice after goals, a tradition since 1996?", "Plastic rats", ["Octopuses", "Catfish", "Hats"], "It started after Scott Mellanby killed a rat in the dressing room with his stick."],
    ["Detroit fans have thrown what on the ice since 1952?", "Octopuses", ["Plastic rats", "Catfish", "Waffles"], "Its eight legs stood for the eight playoff wins it then took to win the Cup."],
    ["What do Nashville fans throw on the ice?", "Catfish", ["Octopuses", "Plastic rats", "Cowboy hats"], "Catfish have landed on the Nashville ice since 2003."],
    # players and people
    ["Which goalie was known as 'The Dominator'?", "Dominik Hasek", ["Patrick Roy", "Ed Belfour", "Martin Brodeur"], "Ed Belfour was 'The Eagle'."],
    ["Who was the first goalie to wear a mask regularly, starting in 1959?", "Jacques Plante", ["Terry Sawchuk", "Glenn Hall", "Johnny Bower"], "He put it on after a shot from Andy Bathgate cut his face."],
    ["Mario Lemieux missed two months for cancer treatment in 1992-93. What did he still win?", "The Art Ross Trophy", ["The Conn Smythe Trophy", "The Calder Trophy", "The Selke Trophy"], "He finished with 160 points in 60 games."],
    ["How old was Gordie Howe in his last NHL season, 1979-80?", "52", ["46", "48", "50"], "He played for Hartford, alongside his sons Mark and Marty."],
    ["Wayne Gretzky began his pro career in the WHA with which team?", "Indianapolis Racers", ["Winnipeg Jets", "Quebec Nordiques", "Houston Aeros"], "Indianapolis sold him to Edmonton after eight games."],
    ["Which team did Wayne Gretzky never play for?", "Vancouver Canucks", ["St. Louis Blues", "New York Rangers", "Los Angeles Kings"], "He played for Edmonton, Los Angeles, St. Louis and the Rangers."],
    ["Who became the youngest captain to win the Stanley Cup, in 2009?", "Sidney Crosby", ["Jonathan Toews", "Steve Yzerman", "Wayne Gretzky"], "Crosby was 21. Toews won the next year at 22."],
    ["Who is the longest-serving captain in NHL history?", "Steve Yzerman", ["Joe Sakic", "Mark Messier", "Alex Delvecchio"], "Yzerman captained Detroit from 1986 until he retired in 2006, winning three Cups."],
    ["Eric Lindros refused to play for which team after it drafted him first overall in 1991?", "Quebec Nordiques", ["Philadelphia Flyers", "New York Rangers", "Toronto Maple Leafs"], "Quebec traded him to Philadelphia a year later."],
    ["Who was the first Black player in the NHL, in 1958?", "Willie O'Ree", ["Grant Fuhr", "Mike Marson", "Jarome Iginla"], "O'Ree played for Boston despite being blind in one eye."],
    ["Who was the first woman to play in an NHL game, a 1992 preseason game?", "Manon Rheaume", ["Hayley Wickenheiser", "Cammi Granato", "Angela Ruggiero"], "She played a period in goal for Tampa Bay."],
    ["How many Sutter brothers played in the NHL?", "6", ["3", "4", "5"], "Brent, Brian, Darryl, Duane, Rich and Ron, all from Viking, Alberta."],
    ["Jaromir Jagr wore number 68 to honour what?", "The Prague Spring of 1968", ["His birth year", "His father's number", "His first junior team"], "That year Soviet troops crushed the reforms in Czechoslovakia."],
    ["Which player was called 'The Finnish Flash'?", "Teemu Selanne", ["Jari Kurri", "Saku Koivu", "Mikko Rantanen"], "He retired in 2014 with 684 goals."],
    ["Which goalie was known as 'King Henrik'?", "Henrik Lundqvist", ["Henrik Sedin", "Henrik Zetterberg", "Pekka Rinne"], "He played his whole NHL career with the Rangers."],
    ["Who bought the Pittsburgh Penguins in 1999 and then came back to play for them?", "Mario Lemieux", ["Sidney Crosby", "Jaromir Jagr", "Ron Francis"], "He returned as a player-owner in December 2000."],
    ["Which team did Wayne Gretzky coach?", "Phoenix Coyotes", ["Los Angeles Kings", "Edmonton Oilers", "New York Rangers"], "He coached Phoenix from 2005 to 2009."],
    ["Which coach won the most Stanley Cups?", "Scotty Bowman", ["Toe Blake", "Al Arbour", "Glen Sather"], "Bowman won nine, with Montreal, Pittsburgh and Detroit. Toe Blake won eight."],
    ["Who coached the Islanders to four straight Cups?", "Al Arbour", ["Scotty Bowman", "Glen Sather", "Fred Shero"], "Arbour came back years later to coach his 1,500th Islanders game."],
    # drafts
    ["Who went first overall in the 2004 draft?", "Alex Ovechkin", ["Evgeni Malkin", "Sidney Crosby", "Patrick Kane"], "Washington took him. Malkin went second to Pittsburgh."],
    ["Who went second overall, after Connor McDavid, in 2015?", "Jack Eichel", ["Mitch Marner", "Noah Hanifin", "Dylan Strome"], "Buffalo took Eichel. He later won the Cup with Vegas."],
    ["Who went second overall, after Auston Matthews, in 2016?", "Patrik Laine", ["Pierre-Luc Dubois", "Jesse Puljujarvi", "Matthew Tkachuk"], "Winnipeg took Laine."],
    ["Who did New Jersey take first overall in 2017?", "Nico Hischier", ["Nolan Patrick", "Miro Heiskanen", "Cale Makar"], "Hischier was the first Swiss player taken first overall."],
    ["Who did Buffalo take first overall in 2018?", "Rasmus Dahlin", ["Andrei Svechnikov", "Quinn Hughes", "Brady Tkachuk"], "Carolina took Svechnikov second."],
    ["Who went first overall in 2019?", "Jack Hughes", ["Kaapo Kakko", "Bowen Byram", "Trevor Zegras"], "New Jersey took him. The Rangers took Kakko second."],
    ["Who did the Rangers take first overall in 2020?", "Alexis Lafreniere", ["Tim Stutzle", "Quinton Byfield", "Jamie Drysdale"], "Los Angeles took Byfield second."],
    ["Who did Buffalo take first overall in 2021?", "Owen Power", ["Matty Beniers", "Mason McTavish", "Luke Hughes"], "Seattle took Beniers second in its first draft."],
    ["Who did Montreal take first overall in 2022?", "Juraj Slafkovsky", ["Shane Wright", "Logan Cooley", "Simon Nemec"], "The draft was held in Montreal that year."],
    ["Who did San Jose take first overall in 2024?", "Macklin Celebrini", ["Ivan Demidov", "Artyom Levshunov", "Cayden Lindstrom"], "Chicago took Levshunov second."],
    ["Who did the Islanders take first overall in 2025?", "Matthew Schaefer", ["Michael Misa", "Ivan Ryabkin", "Porter Martone"], "The Islanders jumped up from 10th in the draft lottery."],
    ["Which team drafted Mario Lemieux first overall in 1984?", "Pittsburgh Penguins", ["New Jersey Devils", "Quebec Nordiques", "Chicago Blackhawks"], "He scored on his first shift, on his first shot, against Boston."],
    # rules and the game
    ["How long is a major penalty?", "5 minutes", ["2 minutes", "4 minutes", "10 minutes"], "A minor is two minutes and a misconduct is ten."],
    ["Starting in 2025-26, how many regular-season games does each team play?", "84", ["80", "82", "86"], "It was 82 from 1995-96 until 2024-25, apart from shortened seasons."],
    ["In which season did the NHL bring in the shootout?", "2005-06", ["1999-00", "2003-04", "2010-11"], "The same season brought the salary cap and the goalie trapezoid."],
    ["What does an NHL puck weigh?", "6 ounces", ["4 ounces", "8 ounces", "10 ounces"], "It is three inches across and one inch thick, and is frozen before games."],
    ["Which rule went away in 2005-06 to speed up the game?", "The two-line pass", ["Icing", "Offside", "The goalie trapezoid"], "Passes across the red line from your own zone became legal."],
    ["How many skaters does each team have on the ice in regular-season overtime?", "3", ["4", "5", "2"], "Overtime has been 3 on 3 since 2015-16. Playoff overtime stays 5 on 5."],
]


def js(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def entry(q):
    return "    [" + js(q[0]) + "," + js(q[1]) + ",[" + ",".join(js(x) for x in q[2]) + "]," + js(q[3]) + "],"


ROUND_OLD = "const start=()=>{round=shuf(Q).slice(0,N).map("
ROUND_NEW = ("const start=()=>{" + MARK + "let seen=[];try{seen=JSON.parse(localStorage.getItem(\"polska-trivseen\")||\"[]\");}catch(e){}"
             "let fresh=Q.filter(q=>!seen.includes(q[0]));if(fresh.length<N){seen=[];fresh=Q;}"
             "const pick=shuf(fresh).slice(0,N);try{localStorage.setItem(\"polska-trivseen\",JSON.stringify([...seen,...pick.map(q=>q[0])]));}catch(e){}"
             "round=pick.map(")


def main(path):
    raw = open(path, "rb").read().decode("utf-8")
    crlf = "\r\n" in raw
    s = raw.replace("\r\n", "\n")
    if MARK in s:
        print("already patched, nothing to do")
        return
    for name, old in (("question bank", ANCHOR), ("round", ROUND_OLD)):
        if s.count(old) != 1:
            sys.exit(f"stopped: the {name} spot was found {s.count(old)} times (expected 1); nothing written")
    add = [entry(q) for q in NEW]
    s = s.replace(ANCHOR, ANCHOR.replace("\n  ];", "\n" + "\n".join(add) + "\n  ];"), 1)
    s = s.replace(ROUND_OLD, ROUND_NEW, 1)
    if crlf:
        s = s.replace("\n", "\r\n")
    open(path, "wb").write(s.encode("utf-8"))
    print(f"patched: {len(NEW)} new trivia questions; rounds favour unseen questions")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "index.html")
