var request = require('request');
var cheerio = require('cheerio');

triggers = [
	'mensa',
	'f[o]{2,}d',
	'essen',
	'hunger',
	'hungry',
	'starving',
	'lunch',
	'eat'
];

module.exports = function (bot) {
	regex = new RegExp(triggers.join('|'), 'gi');
    bot.hear(regex, function (res) {

        var msg = 'Konnte Mensa-Infos nicht abrufen :-(';

        request('http://www.studierendenwerk-mainz.de/speiseplan/frontend/index.php?building_id=1&display_type=1', function (error, response, html) {
            if (!error && response.statusCode == 200) {
                var $ = cheerio.load(html, {
                    normalizeWhitespace: true,
                    decodeEntities: true
                });
                msg = '# Die Mensa empfiehlt:\n';
                $('div.vegan_icon').children().each(function(i, element){
					//console.log($(this));
					if ($(element).attr('src')) {
						if (~$(element).attr('src').indexOf('Veggi.png'))
							$(element).parent().parent().find('span').before(' [Veggi]');
						if (~$(element).attr('src').indexOf('Vegan.png'))
							$(element).parent().parent().find('span').before(' [Vegan]');
					}
				});
				$('div.counter_box').each(function(i, element){
                    var a = $(this).text().replace(/\s*\|\s*/g, '\n');
                    // remove parentheses
                    a = a.replace(/\(.+?\)/g, '');
                    // remove empty lines
                    a = a.replace(/^\s*[\r\n]/gm, '');  // no effect currently...
					// remove multiple spaces
					a = a.replace(/ +(?= )/g,'');
					// insert veggie and vegan icon
					a = a.replace(/\[(Veg.*)\]/g, '![$1](http://www.studierendenwerk-mainz.de/fileadmin/templates/images/speiseplan/$1.png)');
                    // format ausgabe
                    a = a.replace('- Menü', '');
                    a = a.replace(/^\s+(Ausgabe\s\d)\s+(.*)/g, '\n## $1\n$2');
                    //alert($(this));
                    //console.log(a);
                    msg += a + '\n';
					//res.send(a);
                });
            } else {
				res.send(msg);
                return res.send(error);
            }
			
			return res.send(msg);
        });

	});
}

