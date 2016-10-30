
class Iptables():
    def __init__(self):
        self.post_chain = iptc.Chain(iptc.Table(iptc.Table.NAT), 'POSTROUTING')
        self.pre_chain = iptc.Chain(iptc.Table(iptc.Table.NAT), 'PREROUTING')
        self.in_chain = iptc.Chain(iptc.Table(iptc.Table.FILTER), 'INPUT')
        self.out_chain = iptc.Chain(iptc.Table(iptc.Table.FILTER), 'OUTPUT')
        self.fwd_chain = iptc.Chain(iptc.Table(iptc.Table.FILTER), 'FORWARD')


    def ipt_flush(self):
        log = logging.getLogger(self.cls_logger + '.ipt_flush')
        # TODO: Find all chains, flush. Also, move into pycons3rt.
        try:
            self.in_chain.flush()
            self.out_chain.flush()
            self.fwd_chain.flush()
            self.pre_chain.flush()
            self.post_chain.flush()
            log.info('Flushed iptables.')
        except Exception as e:
            log.error('Failed to flush iptables: {}'.format(str(e)))

    def ipt_def_policy(self,chain=None,table=None,pol=None):
        log = logging.getLogger(self.cls_logger + '.ipt_def_policy')
        chains = {'INPUT' : self.in_chain,'OUTPUT' : self.out_chain,'FORWARD': self.fwd_chain,
            'PREROUTING' : self.pre_chain,'POSTROUTING' : self.post_chain}

        policies = ('DROP', 'ACCEPT', 'QUEUE','RETURN')
        if not pol in policies:
            log.error('Policy is invalid')
            return 1

        chains[chain].set_policy(pol)
        log.info('Set default policy on chain: {} to: {}'.format(chain,pol))

    def ipt_estab_related(self,chain=None,proto=None,table=None):
        log = logging.getLogger(self.cls_logger + '.ipt_estab_related')

        chains = {'INPUT' : self.in_chain,'OUTPUT' : self.out_chain,'FORWARD': self.fwd_chain,
            'PREROUTING' : self.pre_chain,'POSTROUTING' : self.post_chain}
        tables = ('FILTER','NAT','MANGLE','RAW')
        protocols = ('tcp','udp','icmp', 'any')

        if not chain in chains:
            log.error('Invalid chain specified.')
            return 1
        if not table in tables:
            log.warn('Invalid or unset table specified. Defaulting')
            table = 'FILTER'
        if not proto in protocols:
            log.warn('Not protocol specified. Defaulting to TCP')
            proto = 'tcp'

        try:
            rule = iptc.Rule()
            #rule.protocol = proto
            rule.target = iptc.Target(rule, 'ACCEPT')
            match = iptc.Match(rule, 'state')
            match.state = 'RELATED,ESTABLISHED'
            rule.add_match(match)
            chains[chain].insert_rule(rule)
            log.info('ESTAB/RELATED rule added to chain: {}'.format(chain))
        except Exception as e:
            log.error('Error adding ESTABLISHED/RELATED rule to {}. Error: {}'.format(chain,str(e)))

    def ipt_add_rule(self,source=None,in_int=None,out_int=None,dport=None,sport=None,table=None,
        proto=None,chain=None):
        log = logging.getLogger(self.cls_logger + '.ipt_add_rule')
        chains = {'INPUT' : self.in_chain,'OUTPUT' : self.out_chain,'FORWARD': self.fwd_chain,
            'PREROUTING' : self.pre_chain,'POSTROUTING' : self.post_chain}
        tables = ('FILTER','NAT','MANGLE','RAW')

        if not chain in chains:
            log.error('Invalid chain specified.')
            return 1
        if not table in tables:
            log.warn('Invalid or unset table specified. Defaulting')
            table = 'FILTER'

        try:
            rule = iptc.Rule()
            if source: rule.src = source 
            if out_int: rule.out_interface = out_int 
            if in_int: rule.in_interface = in_int
            if proto: 
                rule.protocol = proto
                if dport:
                    match = rule.create_match(proto)
                    match.dport = dport
                if sport:
                    match = rule.create_match(proto)
                    match.sport = sport
            rule.create_target('ACCEPT')
            chains[chain].insert_rule(rule)
            log.info('IPT Rule added on chain: {}'.format(chain))
        except Exception as e:
            log.error('Failed to add rule. Error: {}'.format(str(e)))

    def ipt_log(self,chain=None):
        log = logging.getLogger(self.cls_logger + '.ipt_log')
        chains = {'INPUT' : self.in_chain,'OUTPUT' : self.out_chain,'FORWARD': self.fwd_chain,
            'PREROUTING' : self.pre_chain,'POSTROUTING' : self.post_chain}
        if not chain in chains:
            log.error('Invalid chain specified.')
            return 1
        rule = iptc.Rule()
        rule.create_target('LOG')
        chains[chain].insert_rule(rule)
        log.info('Added LOG rule to {} chain'.format(chain))

    def ipt_drop(self,chain=None):
        log = logging.getLogger(self.cls_logger + '.ipt_drop')
        chains = {'INPUT' : self.in_chain,'OUTPUT' : self.out_chain,'FORWARD': self.fwd_chain,
            'PREROUTING' : self.pre_chain,'POSTROUTING' : self.post_chain}
        if not chain in chains:
            log.error('Invalid chain specified.')
            return 1
        rule = iptc.Rule()
        rule.create_target('DROP')
        chains[chain].insert_rule(rule)
        log.info('Added DROP rule to {} chain'.format(chain))

    def masq(self,source=None,out_interface=None):
        log = logging.getLogger(self.cls_logger + '.masq')
        try:
            rule = iptc.Rule()
            rule.source = source
            rule.out_interface = out_interface
            target = iptc.Target(rule, 'MASQUERADE')
            rule.target = target
            self.post_chain.insert_rule(rule)
            log.info('MASQ rule enabled. Source range: {} out interface: {}'.format(source,out_interface))
        except Exception as e:
            log.error('Failed to add MASQ rule. Source: {}. Int: {}. Error: {}'.format(source,
                out_interface,str(e)))

    def redirect_port(self,dport=None,to_port=None,source=None):
        log = logging.getLogger(self.cls_logger + '.redirect_port')
        # configure pre-routing rule for 80->atlassian mapping
        try:
            rule = iptc.Rule()
            rule.protocol = 'tcp'
            match = iptc.Match(rule, 'tcp')
            match.dport = dport
            rule.add_match(match)
            target = iptc.Target(rule,'REDIRECT')
            target.to_ports = to_port
            rule.target = target
            self.pre_chain.insert_rule(rule)
            log.info('Added prerouting rule. DPORT {} redirects to {}.'.format(dport,to_port))
        except Exception as e:
            log.error('Failed to add prerouting rule: {}'.format(str(e)))